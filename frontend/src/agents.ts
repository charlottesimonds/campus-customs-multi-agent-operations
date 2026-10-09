import { Calculator, Crown, MessageSquareText, Package, Store, type LucideIcon } from 'lucide-react'
import type { AgentName } from './api'

export interface AgentIdentity {
  name: AgentName
  label: string
  role: string
  icon: LucideIcon
  // Each agent has one hue, used only for its avatar, its thread line, and its label.
  className: string
}

export const AGENTS: Record<AgentName, AgentIdentity> = {
  boss: { name: 'boss', label: 'Boss', role: 'Coordinates the team and makes the call', icon: Crown, className: 'agent-boss' },
  inventory: { name: 'inventory', label: 'Inventory', role: 'Stock, sizes, vendors, lead times', icon: Package, className: 'agent-inventory' },
  accounting: { name: 'accounting', label: 'Accounting', role: 'Cash, invoices, margins, payments', icon: Calculator, className: 'agent-accounting' },
  facilities: { name: 'facilities', label: 'Facilities', role: 'Lease, rent, the shop space', icon: Store, className: 'agent-facilities' },
  customer_service: { name: 'customer_service', label: 'Customer Service', role: 'Drafts replies, never sends', icon: MessageSquareText, className: 'agent-cs' },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']
