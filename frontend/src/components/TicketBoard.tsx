import { CircleCheck, Play, RotateCcw } from 'lucide-react'
import type { Ticket } from '../api'
import { TICKET_TYPE_LABEL, ticketState } from '../describe'
import { Quatrefoil } from './Emblems'
import { StatusPill, Spinner } from './ui'

function facts(t: Ticket): string[] {
  const out: string[] = []
  if (t.sku) out.push(t.sku)
  if (t.size) out.push(`Size ${t.size}`)
  if (t.qty !== null) out.push(`Qty ${t.qty}`)
  if (t.lease_id !== null) out.push(`Lease ${t.lease_id}`)
  if (t.invoice_id !== null) out.push(`Invoice ${t.invoice_id}`)
  return out
}

export function TicketBoard({
  tickets,
  selectedId,
  starting,
  onSelect,
  onRun,
}: {
  tickets: Ticket[] | null
  selectedId: number | null
  starting: number | null
  onSelect: (id: number) => void
  onRun: (id: number) => void
}) {
  if (!tickets) {
    return (
      <div className="ticket-grid">
        {[0, 1, 2].map((i) => (
          <div key={i} className="ticket-card skeleton" />
        ))}
      </div>
    )
  }
  return (
    <div className="ticket-grid">
      {tickets.map((t) => {
        const state = ticketState(t)
        const resolved = t.status === 'resolved'
        const hasRun = !!t.latest_run && !t.latest_run.before_last_reset
        const isStarting = starting === t.id
        return (
          <article
            key={t.id}
            className={`ticket-card tone-edge-${state.tone}${selectedId === t.id ? ' is-selected' : ''}${resolved ? ' is-resolved' : ''}`}
            onClick={() => onSelect(t.id)}
            tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onSelect(t.id))}
            aria-pressed={selectedId === t.id}
            aria-label={`Ticket ${t.id}: ${t.subject}`}
          >
            <Quatrefoil className="card-orn" size={96} />
            {resolved && (
              <div className="resolved-stamp" aria-hidden>
                <CircleCheck size={15} /> Resolved
              </div>
            )}
            <header className="ticket-top">
              <span className="ticket-number">#{t.id}</span>
              <span className="ticket-type">{TICKET_TYPE_LABEL[t.type] ?? t.type}</span>
            </header>
            <h3 className="ticket-subject">{t.subject}</h3>
            <p className="ticket-requester">from {t.requester}</p>
            {t.notes && <p className="ticket-notes">“{t.notes}”</p>}
            <div className="ticket-facts">
              {facts(t).map((f) => (
                <span key={f} className="fact-chip">{f}</span>
              ))}
            </div>
            <div className="ticket-state">
              <StatusPill tone={state.tone}>{state.label}</StatusPill>
              <p>{state.detail}</p>
            </div>
            <footer className="ticket-actions">
              {resolved ? (
                <span className="muted small">Closed. Review what happened below.</span>
              ) : (
                <button
                  className={`btn ${hasRun ? 'btn-secondary' : 'btn-primary'}`}
                  disabled={t.is_running || isStarting}
                  onClick={(e) => {
                    e.stopPropagation()
                    onRun(t.id)
                  }}
                >
                  {t.is_running || isStarting ? (
                    <>
                      <Spinner size={15} /> Team is working…
                    </>
                  ) : hasRun ? (
                    <>
                      <RotateCcw size={15} /> Run the team again
                    </>
                  ) : (
                    <>
                      <Play size={15} /> Start the team
                    </>
                  )}
                </button>
              )}
            </footer>
          </article>
        )
      })}
    </div>
  )
}
