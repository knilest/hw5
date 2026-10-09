import type { AgentName } from './types'

export interface AgentLook {
  name: AgentName
  title: string
  mark: string // monogram on the agent's seal
  role: string // a short line, shown under the name
  color: string
  tint: string
}

// Each agent gets a seal, an ink color, and a one-line job description, so you
// can tell who's talking at a glance.
export const AGENTS: Record<AgentName, AgentLook> = {
  boss: {
    name: 'boss', title: 'The Boss', mark: 'B',
    role: 'reads the ticket, makes the call', color: '#1f4d2e', tint: '#e3ede5',
  },
  inventory: {
    name: 'inventory', title: 'Inventory', mark: 'In',
    role: 'counts the shelves', color: '#35597a', tint: '#e3eaf1',
  },
  accounting: {
    name: 'accounting', title: 'Accounting', mark: 'Ac',
    role: 'keeps the books', color: '#8a6114', tint: '#f4ecdb',
  },
  facilities: {
    name: 'facilities', title: 'Facilities', mark: 'Fa',
    role: 'minds the shop space', color: '#8b4434', tint: '#f3e4df',
  },
  customer_service: {
    name: 'customer_service', title: 'Customer Service', mark: 'CS',
    role: 'writes to customers', color: '#6a4677', tint: '#efe6f2',
  },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

// Plain-English labels for MCP tools, shown on the tool chips.
export const TOOL_LABELS: Record<string, string> = {
  get_shop_today: 'checked today’s date',
  list_tickets: 'listed tickets',
  list_open_tickets: 'listed open tickets',
  get_ticket: 'read the ticket',
  check_stock: 'checked stock',
  list_sizes_for_sku: 'checked every size',
  get_pricing: 'looked up pricing',
  list_vendors: 'listed vendors',
  get_vendor_status: 'checked the vendor',
  list_open_invoices: 'listed open invoices',
  get_invoice: 'pulled the invoice',
  get_lease: 'pulled the lease',
  get_cash_balance: 'checked cash',
  list_payments: 'listed payments',
  list_board_items: 'checked the board',
  request_payment: 'requested a payment',
  draft_purchase_order: 'drafted a purchase order',
  propose_discount: 'proposed a discount',
  draft_customer_message: 'drafted a customer note',
  update_ticket_status: 'updated the ticket',
  ask_teammate: 'asked a teammate',
}

export const TICKET_TYPE_LABELS: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Discount request',
}

export const money = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const prettyDate = (iso: string) =>
  new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  })
