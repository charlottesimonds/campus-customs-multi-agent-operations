import { ArrowRight, Ban, ChevronDown, CircleAlert, FileText, Inbox, Lock, Play, UserRound, Wrench } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, describeError, type AgentName, type AuditRecord, type RunDetail, type RunSummary, type Ticket } from '../api'
import { AGENTS, AGENT_ORDER } from '../agents'
import { AgentAvatar, AgentTag } from './AgentAvatar'
import {
  DECISION_LABEL,
  TICKET_TYPE_LABEL,
  TOOL_VERB,
  clock,
  duration,
  narrate,
  toolArgs,
  toolResultSummary,
} from '../describe'
import { usePolling, useTicker } from '../hooks'
import { Bulldog } from './Emblems'
import { Empty, Spinner, StatusPill } from './ui'

// ---------------------------------------------------------------------------
// Derived view of a run: who is involved, who is working right now, who asked whom
// ---------------------------------------------------------------------------

interface Seat {
  involved: boolean
  working: boolean
  tools: number
  askedBy: number
  asked: number
}

function seatsFrom(records: AuditRecord[], live: boolean): Record<AgentName, Seat> {
  const seats = Object.fromEntries(
    AGENT_ORDER.map((a) => [a, { involved: false, working: false, tools: 0, askedBy: 0, asked: 0 }]),
  ) as Record<AgentName, Seat>
  const open: Record<string, number> = {}
  for (const r of records) {
    if (r.agent && r.agent in seats) seats[r.agent].involved = true
    if (r.action === 'agent_started' && r.agent) open[r.agent] = (open[r.agent] ?? 0) + 1
    if (r.action === 'agent_finished' && r.agent) open[r.agent] = Math.max(0, (open[r.agent] ?? 0) - 1)
    if (r.action === 'tool_called' && r.agent) seats[r.agent].tools++
    if (r.action === 'delegation_requested' && r.agent && r.to_agent) {
      seats[r.agent].asked++
      seats[r.to_agent].askedBy++
      seats[r.to_agent].involved = true
    }
  }
  if (live) for (const a of AGENT_ORDER) seats[a].working = (open[a] ?? 0) > 0
  return seats
}

function handoffsFrom(records: AuditRecord[]) {
  const edges = new Map<string, { from: AgentName; to: AgentName; count: number; first: string }>()
  for (const r of records) {
    if (r.action !== 'delegation_requested' || !r.agent || !r.to_agent) continue
    const key = `${r.agent}>${r.to_agent}`
    const e = edges.get(key)
    if (e) e.count++
    else edges.set(key, { from: r.agent, to: r.to_agent, count: 1, first: r.detail })
  }
  return [...edges.values()]
}

// ---------------------------------------------------------------------------

export function Workspace({
  ticket,
  onRun,
  starting,
  onRunFinished,
}: {
  ticket: Ticket | null
  onRun: (id: number) => void
  starting: boolean
  onRunFinished: () => void
}) {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [chosenRunId, setChosenRunId] = useState<string | null>(null)
  const latestRunId = ticket?.latest_run && !ticket.latest_run.before_last_reset ? ticket.latest_run.run_id : null
  const runId = chosenRunId ?? latestRunId ?? (ticket?.latest_run?.run_id ?? null)
  const latestStatus = ticket?.latest_run?.status

  // Load the ticket's run history whenever the ticket or its latest run changes.
  // (The parent remounts this component per ticket, so the chosen run resets on its own.)
  useEffect(() => {
    if (!ticket) return
    api.ticket(ticket.id).then((r) => setRuns(r.ticket.runs)).catch(() => setRuns([]))
  }, [ticket?.id, ticket?.latest_run?.run_id, latestStatus]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!ticket) {
    return (
      <section className="panel workspace">
        <Empty icon={<Inbox size={22} />} title="Pick a ticket to follow the team" />
      </section>
    )
  }

  const selectedRun = runs.find((r) => r.run_id === runId) ?? (ticket.latest_run?.run_id === runId ? ticket.latest_run : null)

  return (
    <section className="panel workspace" aria-label="Team at work">
      <header className="panel-head">
        <div>
          <p className="eyebrow">Team at work</p>
          <h2>
            #{ticket.id} · {ticket.subject}
          </h2>
          <p className="muted small">
            {TICKET_TYPE_LABEL[ticket.type] ?? ticket.type} from {ticket.requester}
          </p>
        </div>
        {runs.length > 0 && (
          <label className="run-picker">
            <span className="muted small">Run</span>
            <select value={runId ?? ''} onChange={(e) => setChosenRunId(e.target.value)}>
              {runs.map((r, i) => (
                <option key={r.run_id} value={r.run_id}>
                  {i === 0 ? 'Latest' : `Earlier`} · {new Date(r.started_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })} ·{' '}
                  {r.status === 'completed' && r.decision ? DECISION_LABEL[r.decision].label : r.status}
                  {r.before_last_reset ? ' (before reset)' : ''}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>

      {!runId ? (
        <Empty icon={<Bulldog size={40} />} title="The team hasn’t worked this ticket yet">
          <p>Start a run and you’ll see Boss hand pieces of the problem to the right specialists, live.</p>
          {ticket.status !== 'resolved' && (
            <button className="btn btn-primary" disabled={starting} onClick={() => onRun(ticket.id)}>
              {starting ? <Spinner size={15} /> : <Play size={15} />} Start the team
            </button>
          )}
        </Empty>
      ) : (
        <RunView key={runId} runId={runId} summary={selectedRun} onFinished={onRunFinished} />
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------

function RunView({ runId, summary, onFinished }: { runId: string; summary: RunSummary | null; onFinished: () => void }) {
  const [records, setRecords] = useState<AuditRecord[]>([])
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showTools, setShowTools] = useState(true)
  const cursor = useRef<number | undefined>(undefined)
  const wasRunning = useRef(false)
  const detailLoaded = useRef(false)

  const status = detail?.status ?? summary?.status ?? 'running'
  const live = status === 'running'
  useTicker(live)

  const loadDetail = useCallback(async () => {
    try {
      setDetail(await api.run(runId))
    } catch (e) {
      setError(describeError(e))
    }
  }, [runId])

  const loadActivity = useCallback(async () => {
    if (!detailLoaded.current) {
      detailLoaded.current = true
      await loadDetail()
    }
    try {
      const page = await api.activity({ runId, after: cursor.current })
      if (page.records.length) {
        setRecords((prev) => [...prev, ...page.records.filter((r) => !prev.some((p) => p.seq === r.seq))])
      }
      cursor.current = page.next_cursor
      setError(null)
      const done = page.records.some((r) => r.run_id === runId && (r.action === 'run_completed' || r.action === 'run_failed'))
      if (done || (wasRunning.current && !page.active_runs.some((a) => a.run_id === runId))) {
        if (wasRunning.current) onFinished()
        wasRunning.current = false
        await loadDetail()
      }
      if (page.active_runs.some((a) => a.run_id === runId)) wasRunning.current = true
    } catch (e) {
      setError(describeError(e))
    }
  }, [runId, loadDetail, onFinished])

  // Fast while the team works; slower afterwards to pick up approvals and payments.
  usePolling(loadActivity, live ? 1500 : 5000)

  const seats = useMemo(() => seatsFrom(records, live), [records, live])
  const handoffs = useMemo(() => handoffsFrom(records), [records])
  const items = useMemo(
    () =>
      records
        .map((r) => ({ r, n: narrate(r) }))
        .filter((x): x is { r: AuditRecord; n: NonNullable<ReturnType<typeof narrate>> } => !!x.n)
        .filter((x) => showTools || x.n.kind !== 'tool'),
    [records, showTools],
  )
  const started = summary?.started_at ?? records[0]?.timestamp

  return (
    <div className="run-view">
      <div className="run-meta">
        {live ? (
          <StatusPill tone="working">Live · {started ? duration(started, null) : '…'}</StatusPill>
        ) : status === 'failed' ? (
          <StatusPill tone="error">Run failed</StatusPill>
        ) : status === 'interrupted' ? (
          <StatusPill tone="error">Interrupted</StatusPill>
        ) : (
          <StatusPill tone="neutral">Finished · {started ? duration(started, detail?.finished_at ?? summary?.finished_at ?? null) : ''}</StatusPill>
        )}
        {detail?.usage && (
          <span className="muted small">
            {detail.usage.requests} model calls · {detail.delegations ?? 0} handoffs · {(detail.usage.input_tokens / 1000).toFixed(1)}k tokens in
          </span>
        )}
        {detail?.models_used?.length ? <span className="model-chip">{detail.models_used.join(', ')}</span> : null}
        {summary?.before_last_reset && <span className="muted small">This run happened before the last reset.</span>}
      </div>

      {error && (
        <div className="inline-error">
          <CircleAlert size={16} /> {error}
        </div>
      )}

      {/* The team, seat by seat */}
      <div className="roster" aria-label="Agents">
        {AGENT_ORDER.map((a) => {
          const s = seats[a]
          return (
            <div key={a} className={`seat ${AGENTS[a].className}${s.involved ? ' is-involved' : ' is-idle'}${s.working ? ' is-working' : ''}`}>
              <AgentAvatar agent={a} size={40} pulse={s.working} />
              <div className="seat-text">
                <strong>{AGENTS[a].label}</strong>
                <span>{s.working ? 'Working now…' : s.involved ? `${s.tools} tool call${s.tools === 1 ? '' : 's'}` : 'Not involved'}</span>
                {s.involved && !s.working && (
                  <span>{s.askedBy ? `asked ${s.askedBy}×` : s.asked ? `asked others ${s.asked}×` : 'took the ticket'}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {handoffs.length > 0 && (
        <div className="handoffs">
          <p className="eyebrow">How the work moved</p>
          <div className="handoff-list">
            {handoffs.map((h) => (
              <div key={`${h.from}>${h.to}`} className="handoff" title={h.first}>
                <AgentAvatar agent={h.from} size={22} />
                <ArrowRight size={14} className="muted" />
                <AgentAvatar agent={h.to} size={22} />
                <span>
                  {AGENTS[h.from].label} → {AGENTS[h.to].label}
                  {h.count > 1 && <em> ×{h.count}</em>}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {detail?.status === 'completed' && detail.decision && <Outcome detail={detail} />}
      {detail?.status === 'failed' && (
        <div className="outcome outcome-error">
          <CircleAlert size={20} />
          <div>
            <strong>The run stopped before the team reached a decision.</strong>
            <p>{detail.error}</p>
            <p className="muted small">The ticket is still open. Nothing was paid or sent.</p>
          </div>
        </div>
      )}

      <div className="timeline-head">
        <p className="eyebrow">Step by step</p>
        <label className="toggle">
          <input type="checkbox" checked={showTools} onChange={(e) => setShowTools(e.target.checked)} />
          Show tool calls
        </label>
      </div>
      {items.length === 0 ? (
        <div className="timeline-empty">
          <Spinner /> Waiting for the first step…
        </div>
      ) : (
        <ol className="timeline">
          {items.map(({ r, n }) => (
            <TimelineItem key={r.seq} r={r} n={n} />
          ))}
          {live && (
            <li className="tl-item tl-live">
              <span className="tl-gutter">
                <Spinner size={16} />
              </span>
              <span className="muted">The team is still working…</span>
            </li>
          )}
        </ol>
      )}
    </div>
  )
}

function TimelineItem({ r, n }: { r: AuditRecord; n: NonNullable<ReturnType<typeof narrate>> }) {
  const [open, setOpen] = useState(false)
  const agent = r.agent
  const indent = Math.min(r.depth, 3)
  const result = n.kind === 'tool' ? toolResultSummary(r.tool_name, r.outcome) : null
  return (
    <li className={`tl-item tl-${n.kind}${agent ? ` ${AGENTS[agent].className}` : ''}`} style={{ marginLeft: indent * 22 }}>
      <span className="tl-gutter">
        {agent ? (
          <AgentAvatar agent={agent} size={26} />
        ) : r.actor ? (
          <span className="avatar avatar-human" style={{ width: 26, height: 26 }}>
            <UserRound size={14} />
          </span>
        ) : (
          <span className="avatar avatar-system" style={{ width: 26, height: 26 }}>
            <Lock size={13} />
          </span>
        )}
      </span>
      <div className="tl-content">
        <div className="tl-line">
          <span className="tl-headline">
            {n.kind === 'handoff' && r.to_agent ? (
              <>
                {n.headline.split(' asked ')[0]} <ArrowRight size={13} className="tl-arrow" /> <AgentTag agent={r.to_agent} />
              </>
            ) : n.kind === 'answer' && r.to_agent ? (
              <>
                {n.headline.split(' reported')[0]} <span className="muted">reported back to</span> <AgentTag agent={r.to_agent} />
              </>
            ) : n.kind === 'warning' && r.action === 'delegation_refused' ? (
              <>
                <Ban size={13} /> {n.headline}
              </>
            ) : (
              n.headline
            )}
          </span>
          <time className="tl-time">{clock(r.timestamp)}</time>
        </div>
        {n.kind === 'tool' && (
          <div className={`tool-result${result?.error ? ' is-error' : ''}`}>
            <Wrench size={12} />
            <code>{r.tool_name}</code>
            <span>{result?.text}</span>
            <button className="link-btn" onClick={() => setOpen(!open)}>
              {open ? 'hide' : 'details'}
            </button>
          </div>
        )}
        {n.kind === 'tool' && open && (
          <pre className="raw">
            {toolArgs(r.tool_args) && `args: ${toolArgs(r.tool_args)}\n\n`}
            {pretty(r.outcome)}
          </pre>
        )}
        {n.body && n.kind !== 'tool' && <p className={`tl-body${n.kind === 'handoff' ? ' is-quote' : ''}`}>{n.body}</p>}
      </div>
    </li>
  )
}

function pretty(s: string | null) {
  if (!s) return ''
  try {
    return JSON.stringify(JSON.parse(s), null, 2)
  } catch {
    return s
  }
}

// ---------------------------------------------------------------------------
// Outcome: the decision, told honestly, plus who did what
// ---------------------------------------------------------------------------

function Outcome({ detail }: { detail: RunDetail }) {
  // Runs recorded before Problem 7 kept the decision and summary but not the full resolution.
  const res = detail.resolution ?? {
    decision: detail.decision!, summary: detail.summary ?? '', rationale: '', findings: [], drafts: [], next_steps: [], open_questions: [], outstanding_dependencies: [],
  }
  const legacy = !detail.resolution
  const d = DECISION_LABEL[res.decision]
  const [showEvidence, setShowEvidence] = useState(false)
  const pending = detail.proposals.filter((p) => p.status === 'pending').length
  const truth =
    res.decision === 'resolved'
      ? (res.outstanding_dependencies?.length ?? 0) > 0
        ? `The Boss judged everything within the shop’s control done. ${res.outstanding_dependencies!.length} outside dependenc${res.outstanding_dependencies!.length === 1 ? 'y remains' : 'ies remain'} (listed below); nothing outside the shop has happened yet.`
        : 'The Boss judged everything within the shop’s control done, with no outside dependencies.'
      : res.decision === 'awaiting_approval'
        ? `The agents finished their analysis, but the ticket is not resolved: ${pending ? `${pending} request${pending > 1 ? 's' : ''} need your decision` : 'their recommended actions still need a human'}.`
        : res.decision === 'blocked'
          ? 'The agents finished their analysis, but the ticket is blocked until something else happens.'
          : 'The agents finished their analysis, but the system is missing information needed to decide.'
  const contributions = [...detail.contributions].sort((a, b) => AGENT_ORDER.indexOf(a.agent) - AGENT_ORDER.indexOf(b.agent))

  return (
    <div className={`outcome tone-bg-${d.tone}`}>
      <div className="outcome-head">
        <StatusPill tone={d.tone}>{d.label}</StatusPill>
        <p className="outcome-truth">{truth}</p>
      </div>
      <p className="outcome-summary">{res.summary}</p>

      <p className="eyebrow">Who did what</p>
      <div className="contributions">
        {contributions.map((c) => (
          <div key={c.agent} className={`contribution ${AGENTS[c.agent].className}`}>
            <div className="contribution-head">
              <AgentAvatar agent={c.agent} size={26} />
              <strong>{AGENTS[c.agent].label}</strong>
              {c.asked_by.length > 0 && (
                <span className="muted small">asked by {[...new Set(c.asked_by)].map((a) => AGENTS[a].label).join(', ')}</span>
              )}
            </div>
            {c.summary && <p>{c.summary}</p>}
            <div className="contribution-chips">
              {Object.entries(c.tools_used).map(([tool, count]) => (
                <span key={tool} className="mini-chip" title={tool}>
                  {TOOL_VERB[tool] ?? tool}
                  {count > 1 ? ` ×${count}` : ''}
                </span>
              ))}
              {c.drafts.map((dr, i) => (
                <span key={i} className="mini-chip chip-draft">
                  <FileText size={11} /> Drafted reply to {dr.to}
                </span>
              ))}
              {c.proposed_actions.map((p, i) => (
                <span key={i} className="mini-chip chip-request">Requested: {p}</span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {res.drafts.length > 0 && (
        <>
          <p className="eyebrow">Drafted messages</p>
          {res.drafts.map((dr, i) => (
            <details key={i} className="draft">
              <summary>
                <span className="draft-stamp">Draft · not sent</span>
                <span>
                  To {dr.to} — <em>{dr.subject}</em>
                </span>
                <ChevronDown size={15} className="chev" />
              </summary>
              <pre className="draft-body">{dr.body}</pre>
            </details>
          ))}
        </>
      )}

      {(res.outstanding_dependencies?.length ?? 0) > 0 && (
        <div className="dependencies">
          <p className="eyebrow">Still depends on (outside the shop’s control)</p>
          <ul>{res.outstanding_dependencies!.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}

      {(res.next_steps.length > 0 || res.open_questions.length > 0) && (
        <div className="outcome-lists">
          {res.next_steps.length > 0 && (
            <div>
              <p className="eyebrow">Next steps</p>
              <ul>{res.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
            </div>
          )}
          {res.open_questions.length > 0 && (
            <div>
              <p className="eyebrow">Open questions</p>
              <ul>{res.open_questions.map((s, i) => <li key={i}>{s}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      {legacy ? (
        <p className="muted small">This run was recorded before full outcomes were saved, so its drafts and evidence aren’t available here. Its steps are below.</p>
      ) : (
        <button className="link-btn" onClick={() => setShowEvidence(!showEvidence)}>
          {showEvidence ? 'Hide' : 'Show'} the evidence and reasoning ({res.findings.length} findings)
        </button>
      )}
      {showEvidence && !legacy && (
        <div className="evidence">
          <p>{res.rationale}</p>
          <ul>
            {res.findings.map((f, i) => (
              <li key={i}>
                {f.statement} <span className="source">{f.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
