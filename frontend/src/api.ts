// Typed client for the Campus Customs FastAPI backend (Problem 7).
// Every value the dashboard shows comes from these calls; nothing is mocked.

export const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'
export type Decision = 'resolved' | 'awaiting_approval' | 'blocked' | 'needs_more_information'

export interface RunSummary {
  run_id: string
  ticket_id: number
  started_at: string
  finished_at: string | null
  status: 'running' | 'completed' | 'failed' | 'interrupted'
  decision: Decision | null
  summary: string | null
  error: string | null
  before_last_reset: boolean
  usage?: { requests: number; tool_calls: number; input_tokens: number; output_tokens: number }
  delegations?: number
  models_used?: string[]
  outstanding_dependencies?: string[]
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  latest_run: RunSummary | null
  pending_approval_ids: string[]
  is_running: boolean
}

export interface Finding { statement: string; source: string }
export interface Draft { audience: string; to: string; subject: string; body: string; drafted_by: AgentName; status: 'draft' }
export interface ProposedActionData {
  kind: string
  description: string
  amount: number | null
  payee: string | null
  ref_table: string | null
  ref_id: number | null
  proposed_by: AgentName
}

export interface Resolution {
  ticket_id: number
  decision: Decision
  summary: string
  rationale: string
  findings: Finding[]
  proposed_actions: ProposedActionData[]
  drafts: Draft[]
  next_steps: string[]
  open_questions: string[]
  outstanding_dependencies?: string[]
}

export type ProposalStatus = 'pending' | 'paid' | 'approved' | 'rejected' | 'failed' | 'stale' | 'superseded' | 'invalid'

export interface Proposal extends ProposedActionData {
  proposal_id: string
  run_id: string
  ticket_id: number
  status: ProposalStatus
  proposed_at: string
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  before_last_reset?: boolean
  verification: {
    approvable: boolean
    executes_on_approval: boolean
    problems: string[]
    note?: string
    verified?: {
      kind: 'invoice' | 'rent'
      ref_id: number
      amount: number | null
      payee: string | null
      due_date: string | null
      payable_when_proposed: boolean | null
      reason_if_not_payable: string | null
      balance_after_if_paid: number | null
      checked_at_shop_date: string | null
    }
  }
}

export interface Contribution {
  agent: AgentName
  asked_by: AgentName[]
  requests: string[]
  tools_used: Record<string, number>
  delegated_to: AgentName[]
  refused_delegations: number
  summary: string | null
  proposed_actions: string[]
  drafts: { audience: string; to: string; subject: string }[]
}

export interface RunDetail extends RunSummary {
  resolution: Resolution | null
  proposals: Proposal[]
  contributions: Contribution[]
  event_count: number
}

export interface AuditRecord {
  seq: number
  run_id: string | null
  ticket_id: number | null
  timestamp: string
  action: string
  agent: AgentName | null
  actor: string | null
  depth: number
  chain: AgentName[]
  to_agent: AgentName | null
  tool_name: string | null
  tool_args: Record<string, unknown> | null
  detail: string
  outcome: string | null
  data: Record<string, unknown> | null
}

export interface ProposedPaymentItem {
  proposal_id: string
  ticket_id: number
  description: string
  proposed_by: AgentName
  payee: string | null
  amount: number | null
  payable_alone: boolean
  balance_after_alone: number | null
  reason_alone: string | null
  payable_in_plan: boolean
  balance_after_in_plan: number | null
  reason_in_plan: string | null
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  shop_date_today: string
  proposed_payments: {
    count: number
    total_payable: number
    balance_if_all_approved: number
    all_fit: boolean
    items: ProposedPaymentItem[]
    note: string
  }
}

export interface Health {
  status: string
  model: string
  mcp_tools: string[]
  shop_date_today: string
  active_runs: number
}

export class ApiError extends Error {
  status: number
  code: string
  details: unknown
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    })
  } catch {
    throw new ApiError(0, 'backend_unreachable', `Can't reach the backend at ${API_BASE}.`)
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const err = body?.error
    throw new ApiError(response.status, err?.code ?? 'http_error', err?.message ?? `Request failed (${response.status}).`, err?.details)
  }
  return body as T
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const api = {
  health: () => request<Health>('/api/health'),
  tickets: () => request<{ shop_date_today: string; tickets: Ticket[] }>('/api/tickets'),
  ticket: (id: number) =>
    request<{ shop_date_today: string; ticket: Ticket & { runs: RunSummary[]; approvals: Proposal[] } }>(`/api/tickets/${id}`),
  startRun: (id: number) => post<{ run_id: string; ticket_id: number; status: string; started_at: string }>(`/api/tickets/${id}/run`),
  run: (runId: string) => request<RunDetail>(`/api/runs/${runId}`),
  activity: (params: { runId?: string; ticketId?: number; after?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params.runId) q.set('run_id', params.runId)
    if (params.ticketId !== undefined) q.set('ticket_id', String(params.ticketId))
    if (params.after !== undefined) q.set('after', String(params.after))
    q.set('limit', String(params.limit ?? 1000))
    return request<{ records: AuditRecord[]; next_cursor: number; total_records: number; active_runs: { run_id: string; ticket_id: number }[] }>(
      `/api/activity?${q}`,
    )
  },
  approvals: (status?: ProposalStatus) => request<{ approvals: Proposal[] }>(`/api/approvals${status ? `?status=${status}` : ''}`),
  approve: (id: string, approvedBy: string, note?: string) =>
    post<{ proposal_id: string; status: string; executed: boolean; balance_after?: number; message?: string }>(
      `/api/approvals/${id}/approve`, { approved_by: approvedBy, note: note || null }),
  reject: (id: string, rejectedBy: string, reason?: string) =>
    post<{ proposal_id: string; status: string }>(`/api/approvals/${id}/reject`, { rejected_by: rejectedBy, reason: reason || null }),
  cash: () => request<Cash>('/api/cash'),
  reset: (requestedBy: string) =>
    post<{ status: string; row_counts: Record<string, number> }>('/api/database/reset', { confirm: 'RESET', requested_by: requestedBy }),
}

// Friendlier wording for the backend's error codes.
export function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : 'Something went wrong.'
  const friendly: Record<string, string> = {
    backend_unreachable: `The backend isn't responding at ${API_BASE}. Start it from backend/ with uvicorn main:app --reload --port 8000.`,
    insufficient_cash: "Not enough cash in checking to cover this payment. Nothing was paid.",
    already_paid: 'This has already been paid. Nothing was paid again.',
    run_in_progress: 'The agents are already working on this.',
    stale_proposal: 'This request is out of date (it came before a reset or a newer run). Run the ticket again for a fresh recommendation.',
    approver_not_human: 'Approvals need a person’s name, not an agent’s.',
    database_busy: 'The shop database is busy right now. Try again in a moment.',
  }
  return friendly[error.code] ? `${friendly[error.code]} (${error.message})` : error.message
}
