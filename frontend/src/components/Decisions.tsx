import { Landmark, Package, Receipt, ShieldCheck, Sparkles, TriangleAlert, Wallet } from 'lucide-react'
import type { Cash, Proposal, ProposedPaymentItem } from '../api'
import { AGENTS } from '../agents'
import { AgentAvatar } from './AgentAvatar'
import { money, shopDate } from '../describe'
import { Bulldog, ElmLeaf } from './Emblems'
import { Empty, Spinner, StatusPill } from './ui'

// ---------------------------------------------------------------------------
// Cash: what is really in the bank vs. what has only been proposed
// ---------------------------------------------------------------------------

export function CashCard({ cash, highlight }: { cash: Cash | null; highlight: boolean }) {
  if (!cash) {
    return (
      <section className="panel cash-card">
        <p className="eyebrow">Checking account</p>
        <div className="cash-figure skeleton-text" />
      </section>
    )
  }
  const p = cash.proposed_payments
  const balance = cash.balance
  const segments = p.items.filter((i) => i.payable_in_plan && i.amount)
  const over = !p.all_fit
  return (
    <section className={`panel cash-card${highlight ? ' is-updated' : ''}`} aria-label="Checking balance">
      <ElmLeaf className="cash-leaf" size={110} />
      <p className="eyebrow">
        <Wallet size={13} /> Checking · actual
      </p>
      <p className="cash-figure">{money(balance)}</p>
      <p className="muted small">
        As of {shopDate(cash.as_of)}, from the shop’s cash account. Changes only when an approved payment is recorded.
      </p>

      <div className="meter" role="img" aria-label={`Proposed payments use ${money(p.total_payable)} of ${money(balance)}`}>
        {segments.map((s) => (
          <span
            key={s.proposal_id}
            className="meter-seg"
            style={{ width: `${Math.min(100, ((s.amount ?? 0) / balance) * 100)}%` }}
            title={`${s.description}: ${money(s.amount)}`}
          />
        ))}
        <span className="meter-rest" />
      </div>

      <dl className="cash-rows">
        <div>
          <dt>Proposed, not approved</dt>
          <dd>{p.count ? `− ${money(p.total_payable)}` : money(0)}</dd>
        </div>
        <div className="cash-rows-strong">
          <dt>If every proposal were approved</dt>
          <dd>{money(p.balance_if_all_approved)}</dd>
        </div>
      </dl>
      {p.count > 0 && (
        <p className={`cash-note${over ? ' is-warning' : ''}`}>
          {over ? <TriangleAlert size={14} /> : <ShieldCheck size={14} />}
          {over
            ? 'Not every proposed payment fits. Cash can’t go negative, so some would be refused.'
            : `${p.count} proposed payment${p.count > 1 ? 's' : ''} would fit together. ${p.note.split('.')[0]}.`}
        </p>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// The approval queue
// ---------------------------------------------------------------------------

const KIND_ICON = { payment: Receipt, restock_order: Package, purchase_order: Package, price_override: Sparkles, lease_action: Landmark } as const

function kindLabel(p: Proposal) {
  if (p.kind === 'payment') return p.verification.verified?.kind === 'rent' ? 'Rent payment' : 'Invoice payment'
  return { restock_order: 'Restock order', purchase_order: 'Purchase order', price_override: 'Price change', lease_action: 'Lease action', fulfillment: 'Fulfillment', other: 'Other' }[p.kind] ?? p.kind
}

export function ApprovalQueue({
  approvals,
  cash,
  busyId,
  onApprove,
  onDecline,
}: {
  approvals: Proposal[] | null
  cash: Cash | null
  busyId: string | null
  onApprove: (p: Proposal, preview?: ProposedPaymentItem) => void
  onDecline: (p: Proposal) => void
}) {
  const pending = (approvals ?? []).filter((a) => a.status === 'pending')
  const recent = (approvals ?? [])
    .filter((a) => a.status !== 'pending' && !a.before_last_reset) // a reset undid anything decided before it
    .sort((a, b) => (b.decided_at ?? b.proposed_at).localeCompare(a.decided_at ?? a.proposed_at))
    .slice(0, 6)
  const preview = (id: string) => cash?.proposed_payments.items.find((i) => i.proposal_id === id)

  return (
    <section className="panel approvals" aria-label="Decisions for you">
      <header className="panel-head">
        <div>
          <p className="eyebrow">Needs your decision</p>
          <h2>{approvals === null ? 'Loading…' : pending.length ? `${pending.length} waiting` : 'All clear'}</h2>
        </div>
      </header>
      {approvals === null ? (
        <div className="timeline-empty">
          <Spinner /> Loading requests…
        </div>
      ) : pending.length === 0 ? (
        <Empty icon={<Bulldog size={40} />} title="Nothing needs your sign-off">
          <p>When an agent recommends a payment, purchase, or price change, it lands here. Agents can’t move money on their own.</p>
        </Empty>
      ) : (
        <div className="approval-list">
          {pending.map((p) => {
            const Icon = KIND_ICON[p.kind as keyof typeof KIND_ICON] ?? Receipt
            const pv = preview(p.proposal_id)
            const v = p.verification.verified
            const isPayment = p.kind === 'payment'
            return (
              <article key={p.proposal_id} className={`approval${isPayment ? ' is-payment' : ''}`}>
                <div className="approval-top">
                  <span className="approval-icon">
                    <Icon size={17} />
                  </span>
                  <div className="approval-title">
                    <span className="eyebrow">
                      {kindLabel(p)} · Ticket #{p.ticket_id}
                    </span>
                    <strong>{p.description}</strong>
                  </div>
                  {isPayment && <span className="approval-amount">{money(v?.amount ?? p.amount)}</span>}
                </div>
                <div className="approval-meta">
                  <AgentAvatar agent={p.proposed_by} size={20} />
                  <span>
                    Recommended by {AGENTS[p.proposed_by].label}
                    {isPayment && v?.payee ? ` · to ${v.payee}` : ''}
                    {v?.due_date ? ` · due ${v.due_date}` : ''}
                  </span>
                </div>
                {isPayment ? (
                  pv ? (
                    <div className={`approval-effect${pv.payable_alone ? '' : ' is-warning'}`}>
                      {pv.payable_alone ? (
                        <>
                          <span>Checking after approval</span>
                          <strong>
                            {money(cash?.balance)} → {money(pv.balance_after_alone)}
                          </strong>
                        </>
                      ) : (
                        <>
                          <TriangleAlert size={14} /> <span>{pv.reason_alone}</span>
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="approval-effect">
                      <Spinner size={13} /> Checking the balance…
                    </div>
                  )
                ) : (
                  <div className="approval-effect is-quiet">No money moves. Approving records your decision.</div>
                )}
                <div className="approval-actions">
                  <button className="btn btn-ghost" disabled={busyId === p.proposal_id} onClick={() => onDecline(p)}>
                    Decline
                  </button>
                  <button className="btn btn-primary" disabled={busyId === p.proposal_id} onClick={() => onApprove(p, pv)}>
                    {busyId === p.proposal_id ? <Spinner size={14} /> : null}
                    {isPayment ? 'Review & approve' : 'Approve'}
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}

      {recent.length > 0 && (
        <div className="recent">
          <p className="eyebrow">Recently decided</p>
          <ul>
            {recent.map((p) => (
              <li key={p.proposal_id}>
                <StatusPill tone={recentTone(p.status)}>{recentLabel(p.status)}</StatusPill>
                <span className="recent-text">
                  #{p.ticket_id} · {p.description}
                  {p.decided_by ? <em> — {p.decided_by}</em> : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

const recentLabel = (s: Proposal['status']) =>
  ({ paid: 'Paid', approved: 'Approved', rejected: 'Declined', failed: 'Not paid', stale: 'Expired', superseded: 'Replaced', invalid: 'Invalid', pending: 'Pending' })[s]
const recentTone = (s: Proposal['status']) =>
  s === 'paid' || s === 'approved' ? 'done' : s === 'failed' || s === 'invalid' ? 'error' : 'neutral'
