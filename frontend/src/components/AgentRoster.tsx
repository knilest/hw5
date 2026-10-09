import { AGENTS, AGENT_ORDER } from '../agents'
import type { AgentEvent, AgentName } from '../types'
import { Seal } from './Seal'

type State = 'idle' | 'working' | 'done'

export function agentStates(events: AgentEvent[]): Record<AgentName, State> {
  const states = Object.fromEntries(AGENT_ORDER.map((a) => [a, 'idle'])) as Record<AgentName, State>
  for (const e of events) {
    if (!e.agent) continue
    if (e.step_type === 'final_answer') states[e.agent] = 'done'
    else if (states[e.agent] !== 'done' || e.step_type === 'task_received') states[e.agent] = 'working'
  }
  return states
}

/** Five desks across the top of the floor. A lit seal means that agent is working. */
export function AgentRoster({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const states = agentStates(events)
  const speaking = running ? [...events].reverse().find((e) => e.agent)?.agent : undefined
  return (
    <div className="roster">
      {AGENT_ORDER.map((name) => {
        const look = AGENTS[name]
        const s = states[name]
        return (
          <div key={name} className={`desk desk--${s} ${speaking === name ? 'desk--speaking' : ''}`} style={{ ['--ink' as string]: look.color, ['--tint' as string]: look.tint }}>
            <Seal agent={name} size={44} state={s} />
            <div className="desk__text">
              <span className="desk__name">{look.title}</span>
              <span className="desk__role">{look.role}</span>
              <span className="desk__state">
                {speaking === name ? 'speaking…' : s === 'working' ? (running ? 'at work' : 'stopped') : s === 'done' ? 'reported back' : running ? 'not called yet' : 'not called'}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
