import { AGENTS, AGENT_ORDER, TOOL_LABELS } from '../agents'
import type { AgentEvent, AgentName, AgentReport, TicketDecision } from '../types'
import { Seal } from './Seal'

/** After a run: one index card per agent saying what they did, plus the Boss's decision. */
export function RunSummary({ events }: { events: AgentEvent[] }) {
  const decision = events.find((e) => e.step_type === 'final_answer' && e.chain.length === 1)?.output as
    | TicketDecision
    | undefined

  const reports = new Map<AgentName, AgentReport[]>()
  const tools = new Map<AgentName, Set<string>>()
  for (const e of events) {
    if (!e.agent) continue
    if (e.step_type === 'final_answer' && e.chain.length > 1 && e.output) {
      reports.set(e.agent, [...(reports.get(e.agent) ?? []), e.output as AgentReport])
    }
    for (const c of e.tools_called) {
      if (c.tool === 'final_result') continue
      if (!tools.has(e.agent)) tools.set(e.agent, new Set())
      tools.get(e.agent)!.add(c.tool)
    }
  }

  return (
    <section className="summary">
      {decision && (
        <div className="decision">
          <div className="decision__head">
            <Seal agent="boss" size={46} state="done" />
            <div>
              <span className="eyebrow">The Boss’s decision</span>
              <h3 className={`decision__outcome outcome--${decision.outcome}`}>{decision.outcome.replaceAll('_', ' ')}</h3>
            </div>
          </div>
          <p className="decision__summary">{decision.summary}</p>
          {decision.human_actions_needed.length > 0 && (
            <div className="decision__todo">
              <span className="eyebrow">For you to do</span>
              <ol>
                {decision.human_actions_needed.map((a, i) => (
                  <li key={i}>{a.replace(/^\d+\.\s*/, '')}</li>
                ))}
              </ol>
            </div>
          )}
          <details className="decision__why">
            <summary>Why</summary>
            <p>{decision.rationale}</p>
          </details>
        </div>
      )}

      <h3 className="section-title section-title--small">What each agent did</h3>
      <div className="cards">
        {AGENT_ORDER.map((name) => {
          const look = AGENTS[name]
          const used = [...(tools.get(name) ?? [])]
          const rs = reports.get(name) ?? []
          const called = name === 'boss' ? used.length > 0 : rs.length > 0 || used.length > 0
          return (
            <article
              key={name}
              className={`card ${called ? '' : 'card--absent'}`}
              style={{ ['--ink' as string]: look.color, ['--tint' as string]: look.tint }}
            >
              <header className="card__head">
                <Seal agent={name} size={32} state={called ? 'done' : 'idle'} />
                <div>
                  <span className="card__name">{look.title}</span>
                  <span className="card__role">{look.role}</span>
                </div>
              </header>
              {!called && <p className="card__absent">Not called on this ticket.</p>}
              {name === 'boss' && decision && (
                <p className="card__text">
                  Routed the ticket to {decision.agents_consulted.map((a) => AGENTS[a].title).join(', ') || 'no one'} and
                  closed it as <em>{decision.outcome.replaceAll('_', ' ')}</em>.
                </p>
              )}
              {rs.map((r, i) => (
                <div key={i}>
                  <p className="card__text">{r.summary}</p>
                  {r.actions_taken.length > 0 && (
                    <ul className="card__actions">
                      {r.actions_taken.map((a, j) => <li key={j}>{a}</li>)}
                    </ul>
                  )}
                </div>
              ))}
              {used.length > 0 && (
                <div className="card__tools">
                  {used.map((t) => (
                    <span key={t} className="mini-chip" title={t}>{TOOL_LABELS[t] ?? t}</span>
                  ))}
                </div>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
