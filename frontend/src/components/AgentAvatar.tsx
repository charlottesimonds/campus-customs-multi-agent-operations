import type { AgentName } from '../api'
import { AGENTS } from '../agents'

export function AgentAvatar({ agent, size = 28, pulse = false }: { agent: AgentName; size?: number; pulse?: boolean }) {
  const a = AGENTS[agent]
  const Icon = a.icon
  return (
    <span className={`avatar ${a.className}${pulse ? ' is-pulsing' : ''}`} style={{ width: size, height: size }} title={a.label} aria-hidden>
      <Icon size={Math.round(size * 0.52)} strokeWidth={1.9} />
    </span>
  )
}

export function AgentTag({ agent }: { agent: AgentName }) {
  const a = AGENTS[agent]
  return <span className={`agent-tag ${a.className}`}>{a.label}</span>
}
