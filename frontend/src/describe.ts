// Turns backend records into plain language. Nothing here invents data:
// every number shown is read from a backend response or audit record.

import type { AuditRecord, Decision, Ticket } from './api'
import { AGENTS } from './agents'

export const money = (n: number | null | undefined) =>
  n === null || n === undefined ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const shortMoney = (n: number | null | undefined) =>
  n === null || n === undefined ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: n % 1 ? 2 : 0 })

export function shopDate(iso: string | undefined) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}

export function clock(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit' })
}

export function duration(start: string, end: string | null) {
  const ms = (end ? new Date(end).getTime() : Date.now()) - new Date(start).getTime()
  const s = Math.max(0, Math.round(ms / 1000))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
}

export const TICKET_TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Discount request',
}

// ---------------------------------------------------------------------------
// Ticket status — tells the truth about where a ticket actually stands
// ---------------------------------------------------------------------------

export type Tone = 'neutral' | 'working' | 'attention' | 'blocked' | 'info' | 'done' | 'error'

export interface TicketState {
  label: string
  tone: Tone
  detail: string
}

export const DECISION_LABEL: Record<Decision, { label: string; tone: Tone }> = {
  resolved: { label: 'Resolved', tone: 'done' },
  awaiting_approval: { label: 'Waiting on approval', tone: 'attention' },
  blocked: { label: 'Blocked', tone: 'blocked' },
  needs_more_information: { label: 'Needs information', tone: 'info' },
}

export function ticketState(t: Ticket): TicketState {
  const pending = t.pending_approval_ids.length
  const waiting = pending ? `${pending} decision${pending > 1 ? 's' : ''} waiting for you.` : ''
  if (t.status === 'resolved') {
    const deps = t.latest_run?.outstanding_dependencies?.length ?? 0
    return {
      label: 'Resolved',
      tone: 'done',
      detail: deps
        ? `Closed in the shop’s records. Still depends on ${deps} thing${deps > 1 ? 's' : ''} outside the shop’s control.`
        : 'Closed in the shop’s records.',
    }
  }
  if (t.is_running) return { label: 'Agents working', tone: 'working', detail: 'The team is investigating now.' }
  const run = t.latest_run
  if (!run) return { label: 'Not started', tone: 'neutral', detail: 'No agent run yet.' }
  if (run.before_last_reset) return { label: 'Not started', tone: 'neutral', detail: 'Earlier runs happened before the last reset.' }
  if (run.status === 'failed') return { label: 'Run failed', tone: 'error', detail: 'The last run stopped with an error. Still open.' }
  if (run.status === 'interrupted') return { label: 'Run interrupted', tone: 'error', detail: 'The last run never finished. Still open.' }
  if (!run.decision) return { label: 'Open', tone: 'neutral', detail: 'Still open.' }
  const d = DECISION_LABEL[run.decision]
  if (run.decision === 'resolved') {
    // The Boss said resolved but the shop record hasn't caught up: say so.
    return { label: 'Agents say resolved', tone: 'info', detail: 'Not yet closed in the shop’s records.' }
  }
  const base = run.decision === 'awaiting_approval'
    ? (pending ? waiting : 'Agents finished. No approval requests are pending.')
    : run.decision === 'blocked' ? 'Something must happen first.' : 'Data the team needs is missing.'
  return { label: d.label, tone: d.tone, detail: `${base} Still open.` }
}

// ---------------------------------------------------------------------------
// Tool calls → a short, human summary of what came back
// ---------------------------------------------------------------------------

export const TOOL_VERB: Record<string, string> = {
  get_ticket: 'reread the ticket',
  list_open_tickets: 'looked over the open tickets',
  list_tickets: 'looked over all tickets',
  get_product_stock_and_pricing: 'checked stock and price',
  evaluate_price_override: 'ran the numbers on a price',
  list_vendors: 'reviewed the vendors',
  check_vendor_invoice_status: 'checked a vendor’s invoices',
  get_lease_rent_status: 'looked up the lease',
  get_cash_balance: 'checked the cash balance',
  get_payment_history: 'checked payment history',
  preview_payment_plan: 'previewed a payment',
  record_approved_payment: 'recorded an approved payment',
  update_ticket_status: 'updated the ticket status',
  reset_working_database_to_original: 'reset the working database',
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = Record<string, any>

export function toolResultSummary(tool: string | null, outcome: string | null): { text: string; error: boolean } {
  if (!outcome) return { text: '', error: false }
  if (outcome.startsWith('error:')) return { text: outcome.slice(6).trim(), error: true }
  let r: Json
  try {
    r = JSON.parse(outcome)
  } catch {
    return { text: outcome.length > 220 ? `${outcome.slice(0, 220)}…` : outcome, error: false }
  }
  if (r.found === false) return { text: r.message ?? 'Not found.', error: false }
  try {
    switch (tool) {
      case 'get_ticket':
        return { text: `Ticket ${r.ticket.id}: ${r.ticket.subject} (${r.ticket.status})`, error: false }
      case 'list_open_tickets':
      case 'list_tickets':
        return { text: `${r.tickets.length} tickets`, error: false }
      case 'get_product_stock_and_pricing': {
        const stock = (r.stock as Json[]).map((s) => `${s.size}: ${s.qty}`).join(' · ')
        return { text: `${r.stock[0]?.name ?? r.sku} — ${stock} on hand · cost ${money(r.pricing?.unit_cost)} · list ${money(r.pricing?.list_price)}`, error: false }
      }
      case 'evaluate_price_override':
        return {
          text: `${money(r.at_proposed_price.unit_price)}/unit × ${r.quantity}: margin ${money(r.at_proposed_price.unit_margin)} (${r.at_proposed_price.margin_pct}%) vs ${money(r.at_list_price.unit_margin)} at list${r.below_or_at_cost ? ' · AT OR BELOW COST' : ''}`,
          error: false,
        }
      case 'list_vendors': {
        const blocked = (r.vendors as Json[]).filter((v) => !v.can_ship_new_inventory).map((v) => v.name)
        return { text: `${r.vendors.length} vendors · ${blocked.length ? `can’t ship: ${blocked.join(', ')}` : 'all can ship'}`, error: false }
      }
      case 'check_vendor_invoice_status':
        return {
          text: `${r.vendor.name}: ${r.unpaid_invoice_ids.length ? `${r.unpaid_invoice_ids.length} unpaid (${money(r.total_unpaid)})` : 'no unpaid invoices'} · ${r.can_ship_new_inventory ? 'can ship' : 'cannot ship'}`,
          error: false,
        }
      case 'get_lease_rent_status':
        return { text: `${r.lease.space_name}: ${money(r.lease.monthly_rent)} due ${r.lease.next_due} (${r.is_overdue ? 'overdue' : `in ${r.days_until_due} days`})`, error: false }
      case 'get_cash_balance':
        return { text: (r.accounts as Json[]).map((a) => `${a.name} ${money(a.balance)}`).join(' · '), error: false }
      case 'get_payment_history':
        return { text: r.payments.length ? `${r.payments.length} payment(s) on record` : 'No matching payments recorded', error: false }
      case 'preview_payment_plan':
        return {
          text: `${money(r.starting_balance)} → ${money(r.ending_balance_if_all_payable_items_paid)} if paid · ${r.all_items_payable ? 'all payable' : 'not all payable'} (preview only)`,
          error: false,
        }
      case 'record_approved_payment':
        return r.status === 'paid'
          ? { text: `Paid ${money(r.payment.amount)} · balance now ${money(r.balance_after)}`, error: false }
          : { text: r.reason ?? 'Rejected', error: true }
    }
  } catch {
    /* fall through to raw text */
  }
  return { text: outcome.length > 220 ? `${outcome.slice(0, 220)}…` : outcome, error: false }
}

// ---------------------------------------------------------------------------
// Audit records → one line of narration each
// ---------------------------------------------------------------------------

export interface Narration {
  headline: string
  body?: string
  kind: 'handoff' | 'answer' | 'tool' | 'decision' | 'human' | 'warning' | 'start' | 'error' | 'quiet'
}

const name = (a: string | null | undefined) => (a && a in AGENTS ? AGENTS[a as keyof typeof AGENTS].label : a ?? 'Backend')

export function narrate(r: AuditRecord): Narration | null {
  const data = (r.data ?? {}) as Json
  switch (r.action) {
    case 'run_started':
      return { headline: 'Ticket handed to the team', kind: 'start' }
    case 'agent_started':
      return r.depth === 0 ? { headline: `${name(r.agent)} picked up the ticket`, kind: 'start' } : null // handoffs already show the request
    case 'tool_called':
      if (r.detail === 'blocked') return { headline: `${name(r.agent)} was blocked from ${r.tool_name}`, body: r.outcome ?? '', kind: 'error' }
      return { headline: `${name(r.agent)} ${TOOL_VERB[r.tool_name ?? ''] ?? `used ${r.tool_name}`}`, kind: 'tool' }
    case 'delegation_requested':
      return { headline: `${name(r.agent)} asked ${name(r.to_agent)} for help`, body: r.detail, kind: 'handoff' }
    case 'delegation_refused':
      return { headline: `${name(r.agent)}’s request to ${name(r.to_agent)} was held back`, body: r.outcome ?? '', kind: 'warning' }
    case 'delegation_answered':
      return { headline: `${name(r.agent)} reported back to ${name(r.to_agent)}`, body: r.outcome ?? '', kind: 'answer' }
    case 'agent_finished':
      return r.detail === 'failed' ? { headline: `${name(r.agent)} hit an error`, body: r.outcome ?? '', kind: 'error' } : null
    case 'run_completed': {
      // Runs from before Problem 7 kept the decision only in the detail text ("decision=blocked; ...").
      const decision = (data.decision as Decision | undefined) ?? (/decision=(\w+)/.exec(r.detail)?.[1] as Decision | undefined)
      const d = decision ? DECISION_LABEL[decision] : undefined
      return { headline: d ? `Boss decided: ${d.label}` : 'Boss made the final call', body: r.outcome ?? '', kind: 'decision' }
    }
    case 'run_failed':
      return { headline: 'The run stopped', body: r.outcome ?? '', kind: 'error' }
    case 'action_proposed':
      return {
        headline: `${name(r.agent)} put a request in your queue`,
        body: `${r.detail}${data.amount ? ` — ${money(data.amount as number)}` : ''}`,
        kind: 'human',
      }
    case 'action_approved':
      return { headline: `${r.actor} approved`, body: r.outcome ?? r.detail, kind: 'human' }
    case 'action_rejected':
      return { headline: `${r.actor} declined`, body: `${r.detail}${r.outcome ? ` — “${r.outcome}”` : ''}`, kind: 'human' }
    case 'payment_recorded':
      return { headline: 'Payment recorded', body: r.outcome ?? '', kind: 'decision' }
    case 'payment_failed':
      return { headline: 'Payment not made', body: r.outcome ?? '', kind: 'error' }
    case 'ticket_status_updated':
      return { headline: 'Ticket status updated', body: r.outcome ?? '', kind: 'decision' }
    case 'database_reset':
      return { headline: `${r.actor} reset the shop data`, body: r.outcome ?? '', kind: 'warning' }
  }
  return null
}

export function toolArgs(args: Record<string, unknown> | null): string {
  if (!args) return ''
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .join(', ')
}
