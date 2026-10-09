import { AGENTS } from '../agents'
import type { AgentName } from '../types'

/** A wax-seal style monogram for one agent. */
export function Seal({ agent, size = 40, state }: { agent: AgentName; size?: number; state?: 'idle' | 'working' | 'done' }) {
  const look = AGENTS[agent]
  return (
    <span
      className={`seal seal--${state ?? 'plain'}`}
      style={{ width: size, height: size, fontSize: size * 0.38, background: look.color, ['--ink' as string]: look.color }}
      title={look.title}
      aria-label={look.title}
    >
      <span className="seal__ring" />
      {look.mark}
    </span>
  )
}
