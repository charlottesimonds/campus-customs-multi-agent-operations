import { CircleAlert, RotateCcw, TriangleAlert, Unplug, Wallet } from 'lucide-react'
import { useCallback, useMemo, useRef, useState } from 'react'
import { API_BASE, api, describeError, type Cash, type Health, type Proposal, type ProposedPaymentItem, type Ticket } from './api'
import { AGENTS } from './agents'
import { AgentAvatar } from './components/AgentAvatar'
import { ApprovalQueue, CashCard } from './components/Decisions'
import { Bulldog, GothicTower, Pennant, Quatrefoil, Skyline } from './components/Emblems'
import { TicketBoard } from './components/TicketBoard'
import { Modal, Spinner, Toasts, type Toast } from './components/ui'
import { Workspace } from './components/Workspace'
import { money, shopDate } from './describe'
import { useOperatorName, usePolling } from './hooks'

export default function App() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [approvals, setApprovals] = useState<Proposal[] | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [offline, setOffline] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [starting, setStarting] = useState<number | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [cashFlash, setCashFlash] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [approving, setApproving] = useState<{ p: Proposal; preview?: ProposedPaymentItem } | null>(null)
  const [declining, setDeclining] = useState<Proposal | null>(null)
  const [resetting, setResetting] = useState(false)
  const lastBalance = useRef<number | null>(null)

  const toast = useCallback((t: Omit<Toast, 'id'>) => {
    const id = Date.now() + Math.random()
    setToasts((all) => [...all, { ...t, id }])
    window.setTimeout(() => setToasts((all) => all.filter((x) => x.id !== id)), t.tone === 'error' ? 9000 : 5000)
  }, [])

  const refreshMoney = useCallback(async () => {
    const [c, a] = await Promise.all([api.cash(), api.approvals()])
    if (lastBalance.current !== null && c.balance !== lastBalance.current) {
      setCashFlash(true)
      window.setTimeout(() => setCashFlash(false), 2400)
    }
    lastBalance.current = c.balance
    setCash(c)
    setApprovals(a.approvals)
  }, [])

  const refreshAll = useCallback(async () => {
    try {
      const [t] = await Promise.all([api.tickets(), refreshMoney(), health ? Promise.resolve() : api.health().then(setHealth)])
      setTickets(t.tickets)
      setOffline(null)
      setSelectedId((current) => current ?? pickDefault(t.tickets))
    } catch (e) {
      setOffline(describeError(e))
    }
  }, [refreshMoney, health])

  const anyRunning = !!tickets?.some((t) => t.is_running)
  usePolling(refreshAll, anyRunning ? 2000 : 5000)

  const selected = tickets?.find((t) => t.id === selectedId) ?? null

  // -- actions ----------------------------------------------------------------

  const startRun = async (id: number) => {
    setStarting(id)
    setSelectedId(id)
    try {
      await api.startRun(id)
      toast({ tone: 'info', title: `Team started on ticket #${id}`, message: 'Boss is reading the ticket. Follow along in “Team at work”.' })
      await refreshAll()
    } catch (e) {
      toast({ tone: 'error', title: 'Couldn’t start the team', message: describeError(e) })
    } finally {
      setStarting(null)
    }
  }

  const onRunFinished = useCallback(() => {
    refreshAll()
    toast({ tone: 'info', title: 'The team finished a run', message: 'Check the outcome and anything waiting for your decision.' })
  }, [refreshAll, toast])

  const approve = async (name: string, note: string) => {
    if (!approving) return
    const { p } = approving
    setBusyId(p.proposal_id)
    try {
      const r = await api.approve(p.proposal_id, name, note)
      toast(
        r.executed
          ? { tone: 'success', title: 'Payment recorded', message: `${p.description}. Checking is now ${money(r.balance_after)}.` }
          : { tone: 'success', title: 'Approved', message: r.message ?? 'Your decision was recorded.' },
      )
      setApproving(null)
    } catch (e) {
      toast({ tone: 'error', title: 'Not approved', message: describeError(e) })
      setApproving(null)
    } finally {
      setBusyId(null)
      refreshAll()
    }
  }

  const decline = async (name: string, reason: string) => {
    if (!declining) return
    setBusyId(declining.proposal_id)
    try {
      await api.reject(declining.proposal_id, name, reason)
      toast({ tone: 'info', title: 'Declined', message: `${declining.description}. Nothing changed in the shop’s data.` })
      setDeclining(null)
    } catch (e) {
      toast({ tone: 'error', title: 'Couldn’t decline', message: describeError(e) })
    } finally {
      setBusyId(null)
      refreshAll()
    }
  }

  const reset = async (name: string) => {
    try {
      await api.reset(name)
      toast({ tone: 'success', title: 'Shop data reset', message: 'The working database matches the original again. Your audit history was kept.' })
      setResetting(false)
    } catch (e) {
      toast({ tone: 'error', title: 'Reset refused', message: describeError(e) })
    } finally {
      refreshAll()
    }
  }

  // -- at-a-glance summary -------------------------------------------------------

  const glance = useMemo(() => {
    if (!tickets) return null
    const pending = approvals?.filter((a) => a.status === 'pending').length ?? 0
    const running = tickets.filter((t) => t.is_running).length
    const resolved = tickets.filter((t) => t.status === 'resolved').length
    return { pending, running, resolved, total: tickets.length }
  }, [tickets, approvals])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden>CC</span>
          <div>
            <p className="brand-name">Campus Customs</p>
            <p className="brand-sub">Operations desk</p>
          </div>
        </div>
        <div className="topbar-mid">
          <span className="date-chip">Shop date · {shopDate(health?.shop_date_today ?? cash?.shop_date_today)}</span>
          <span className={`conn ${offline ? 'is-off' : health ? 'is-on' : ''}`}>
            {offline ? <Unplug size={13} /> : <span className="conn-dot" />}
            {offline ? 'Backend offline' : health ? `Connected · ${health.model}` : 'Connecting…'}
          </span>
        </div>
        <div className="topbar-right">
          <a className={`cash-chip${cashFlash ? ' is-updated' : ''}`} href="#decisions">
            <Wallet size={15} />
            <span className="muted">Checking</span>
            <strong>{cash ? money(cash.balance) : '—'}</strong>
          </a>
          <button className="btn btn-ghost btn-small" onClick={() => setResetting(true)} disabled={!!offline}>
            <RotateCcw size={14} /> Reset shop data
          </button>
        </div>
      </header>

      {offline && (
        <div className="banner banner-error" role="alert">
          <CircleAlert size={18} />
          <div>
            <strong>Can’t reach the backend.</strong> {offline}
            <span className="muted"> Retrying automatically.</span>
          </div>
        </div>
      )}

      <main className="desk">
        <section className="desk-intro">
          <GothicTower className="intro-tower" size={250} />
          <div className="intro-text">
            <Bulldog className="intro-bulldog" size={76} title="Campus Customs bulldog" />
            <div>
            <p className="eyebrow">Today at the desk</p>
            <h1>
              {glance ? (
                <>
                  {glance.pending > 0 ? (
                    <><em>{glance.pending}</em> decision{glance.pending > 1 ? 's' : ''} waiting on you</>
                  ) : glance.running > 0 ? (
                    <>The team is <em>working</em></>
                  ) : (
                    <>{glance.total - glance.resolved} of {glance.total} tickets still open</>
                  )}
                </>
              ) : (
                'Opening the desk…'
              )}
            </h1>
            {glance && (
              <p className="desk-sub">
                {glance.running} run{glance.running === 1 ? '' : 's'} in progress · {glance.resolved} of {glance.total} tickets resolved ·{' '}
                {glance.pending} approval{glance.pending === 1 ? '' : 's'} pending
              </p>
            )}
            </div>
          </div>
          <div className="team-strip" aria-label="The team">
            {Object.values(AGENTS).map((a) => (
              <div key={a.name} className="team-member" title={a.role}>
                <AgentAvatar agent={a.name} size={30} />
                <span>{a.label}</span>
              </div>
            ))}
          </div>
        </section>

        <section aria-label="Tickets">
          <div className="section-title">
            <h2><Quatrefoil className="orn" /> Tickets</h2>
            <p className="muted small">Select a ticket to follow the team; start a run when you’re ready.</p>
          </div>
          <TicketBoard tickets={tickets} selectedId={selectedId} starting={starting} onSelect={setSelectedId} onRun={startRun} />
        </section>

        <div className="desk-columns">
          <Workspace key={selected?.id ?? 'none'} ticket={selected} onRun={startRun} starting={starting === selected?.id} onRunFinished={onRunFinished} />
          <aside className="decisions" id="decisions">
            <CashCard cash={cash} highlight={cashFlash} />
            <ApprovalQueue
              approvals={approvals}
              cash={cash}
              busyId={busyId}
              onApprove={(p, preview) => setApproving({ p, preview })}
              onDecline={setDeclining}
            />
          </aside>
        </div>
      </main>

      <footer className="foot">
        <Skyline className="foot-skyline" />
        <div className="foot-line">
          <Pennant className="foot-pennant" size={150} />
          <span>New Haven, Connecticut</span>
        </div>
        Data from the Campus Customs backend at {API_BASE} via MCP · agents run on {health?.model ?? 'gpt-6-luna'} · messages are drafts and are never sent
      </footer>

      {approving && (
        <ApproveDialog
          p={approving.p}
          preview={approving.preview}
          balance={cash?.balance ?? null}
          busy={busyId === approving.p.proposal_id}
          onCancel={() => setApproving(null)}
          onConfirm={approve}
        />
      )}
      {declining && (
        <DeclineDialog p={declining} busy={busyId === declining.proposal_id} onCancel={() => setDeclining(null)} onConfirm={decline} />
      )}
      {resetting && <ResetDialog activeRuns={glance?.running ?? 0} onCancel={() => setResetting(false)} onConfirm={reset} />}
      <Toasts toasts={toasts} dismiss={(id) => setToasts((all) => all.filter((t) => t.id !== id))} />
    </div>
  )
}

function pickDefault(tickets: Ticket[]): number | null {
  return (tickets.find((t) => t.is_running) ?? tickets.find((t) => t.pending_approval_ids.length) ?? tickets.find((t) => t.status !== 'resolved') ?? tickets[0])?.id ?? null
}

// ---------------------------------------------------------------------------
// Dialogs
// ---------------------------------------------------------------------------

function NameField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <label className="field">
      <span>Your name</span>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder="e.g. Charlotte Simonds" autoComplete="name" />
    </label>
  )
}

function ApproveDialog({
  p,
  preview,
  balance,
  busy,
  onCancel,
  onConfirm,
}: {
  p: Proposal
  preview?: ProposedPaymentItem
  balance: number | null
  busy: boolean
  onCancel: () => void
  onConfirm: (name: string, note: string) => void
}) {
  const [name, setName] = useOperatorName()
  const [note, setNote] = useState('')
  const v = p.verification.verified
  const isPayment = p.kind === 'payment'
  const ok = name.trim().length > 1
  return (
    <Modal
      title={isPayment ? 'Approve this payment?' : 'Approve this action?'}
      onClose={onCancel}
      footer={
        <>
          <button className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="btn btn-primary" disabled={!ok || busy} onClick={() => onConfirm(name.trim(), note.trim())}>
            {busy && <Spinner size={14} />} {isPayment ? `Approve & pay ${money(v?.amount ?? p.amount)}` : 'Approve'}
          </button>
        </>
      }
    >
      <p className="dialog-lead">{p.description}</p>
      {isPayment ? (
        <dl className="dialog-facts">
          <div><dt>Pays</dt><dd>{v?.payee}</dd></div>
          <div><dt>For</dt><dd>{v?.kind === 'rent' ? `Lease ${v.ref_id}, rent due ${v.due_date}` : `Invoice ${v?.ref_id}, due ${v?.due_date}`}</dd></div>
          <div><dt>Amount</dt><dd className="num">{money(v?.amount ?? p.amount)}</dd></div>
          <div><dt>Checking now</dt><dd className="num">{money(balance)}</dd></div>
          <div className="dialog-facts-strong">
            <dt>Checking after</dt>
            <dd className="num">{preview?.payable_alone ? money(preview.balance_after_alone) : '—'}</dd>
          </div>
        </dl>
      ) : (
        <p className="muted">No money moves and no database record changes. Your approval is recorded in the audit trail.</p>
      )}
      {isPayment && preview && !preview.payable_alone && (
        <p className="cash-note is-warning"><TriangleAlert size={14} /> {preview.reason_alone} The backend will refuse it.</p>
      )}
      {isPayment && (
        <p className="muted small">
          Recommended by {AGENTS[p.proposed_by].label}. Before paying, the backend checks again that this hasn’t been paid, the amount hasn’t changed, and checking can cover it.
        </p>
      )}
      <NameField value={name} onChange={setName} />
      <label className="field">
        <span>Note for the team (optional)</span>
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Conditions or instructions the agents should follow" />
      </label>
    </Modal>
  )
}

function DeclineDialog({ p, busy, onCancel, onConfirm }: { p: Proposal; busy: boolean; onCancel: () => void; onConfirm: (name: string, reason: string) => void }) {
  const [name, setName] = useOperatorName()
  const [reason, setReason] = useState('')
  return (
    <Modal
      title="Decline this request?"
      onClose={onCancel}
      footer={
        <>
          <button className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="btn btn-danger" disabled={name.trim().length < 2 || busy} onClick={() => onConfirm(name.trim(), reason.trim())}>
            {busy && <Spinner size={14} />} Decline
          </button>
        </>
      }
    >
      <p className="dialog-lead">{p.description}</p>
      <p className="muted">Nothing is paid or changed. The decision is recorded so the team’s history stays complete.</p>
      <NameField value={name} onChange={setName} />
      <label className="field">
        <span>Reason (optional)</span>
        <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Waiting for the club to confirm quantity" />
      </label>
    </Modal>
  )
}

function ResetDialog({ activeRuns, onCancel, onConfirm }: { activeRuns: number; onCancel: () => void; onConfirm: (name: string) => Promise<void> }) {
  const [name, setName] = useOperatorName()
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const ok = typed === 'RESET' && name.trim().length > 1 && activeRuns === 0
  return (
    <Modal
      title="Reset all shop data?"
      onClose={onCancel}
      footer={
        <>
          <button className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button
            className="btn btn-danger"
            disabled={!ok || busy}
            onClick={async () => {
              setBusy(true)
              await onConfirm(name.trim())
              setBusy(false)
            }}
          >
            {busy && <Spinner size={14} />} Reset shop data
          </button>
        </>
      }
    >
      <p className="dialog-lead">This restores the working database to the original data pack.</p>
      <ul className="dialog-list">
        <li>Cash, invoices, the lease, payments, and ticket statuses go back to their starting values.</li>
        <li>Any recorded payments are undone in the working copy. The original database is never touched.</li>
        <li>Pending approval requests expire, because they were based on the old data.</li>
        <li>The audit trail of past runs and decisions is kept.</li>
      </ul>
      {activeRuns > 0 && (
        <p className="cash-note is-warning"><TriangleAlert size={14} /> A run is in progress. Wait for it to finish before resetting.</p>
      )}
      <NameField value={name} onChange={setName} />
      <label className="field">
        <span>Type <code>RESET</code> to confirm</span>
        <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="RESET" autoComplete="off" />
      </label>
    </Modal>
  )
}
