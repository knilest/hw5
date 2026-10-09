export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

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
  state: 'open' | 'resolved'
  running: boolean
}

export interface ToolCall {
  tool: string
  call_id?: string
  args: Record<string, unknown>
}

export interface ToolResult {
  tool: string
  call_id?: string
  result: string
}

export interface AgentReport {
  agent: AgentName
  summary: string
  facts: string[]
  actions_taken: string[]
  board_item_ids: number[]
  needs_human: boolean
  recommendation: string
  open_questions: string[]
}

export interface TicketDecision {
  ticket_id: number
  outcome: 'resolved' | 'waiting_on_approval' | 'declined' | 'needs_more_info'
  summary: string
  agents_consulted: AgentName[]
  board_item_ids: number[]
  human_actions_needed: string[]
  customer_message_drafted: boolean
  rationale: string
}

export interface AgentEvent {
  time: string
  run_id: string | null
  ticket_id: number | null
  agent: AgentName | null
  chain: AgentName[]
  step: number
  step_type: 'task_received' | 'model_request' | 'model_response' | 'final_answer' | 'error' | 'reset' | string
  said: string | null
  tools_called: ToolCall[]
  tool_results: ToolResult[]
  output: AgentReport | TicketDecision | null
}

export type BoardKind = 'payment' | 'purchase_order' | 'discount' | 'customer_message'

export interface BoardItem {
  id: number
  ticket_id: number | null
  kind: BoardKind
  title: string
  amount: number | null
  details: Record<string, any>
  status: 'pending' | 'draft' | 'approved' | 'executed' | 'rejected'
  created_by: string
  created_at: string
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
}

export interface Payment {
  id: number
  kind: string
  ref_id: number
  amount: number
  account: string
  paid_at: string
  approved_by: string
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  pending_requests: number
  pending_amount: number
  balance_if_all_pending_approved: number
  payments: Payment[]
}

export interface RunInfo {
  run_id: string
  ticket_id: number
  status: 'running' | 'done' | 'error'
  started: string
  decision: TicketDecision | null
  error: string | null
}
