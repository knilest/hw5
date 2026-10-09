import { useEffect, useMemo, useRef } from 'react'
import { AGENTS, TOOL_LABELS } from '../agents'
import type { AgentEvent, AgentReport, TicketDecision, ToolCall } from '../types'
import { Seal } from './Seal'

const HIDDEN_TOOLS = new Set(['final_result', 'ask_teammate'])
const QUIET_ARGS = new Set(['requested_by', 'written_by', 'updated_by', 'reason', 'body', 'note', 'subject', 'ticket_id'])

function argSummary(call: ToolCall): string {
  return Object.entries(call.args)
    .filter(([k, v]) => !QUIET_ARGS.has(k) && v !== null && v !== '' && String(v).length < 40)
    .map(([k, v]) => (k === 'qty' ? `×${v}` : k.endsWith('_id') ? `#${v}` : String(v)))
    .join(' · ')
}

function prettyResult(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

interface Props {
  events: AgentEvent[]
  running: boolean
}

/** The floor: every step of the run as it happens, indented by who asked whom. */
export function LiveFeed({ events, running }: Props) {
  const bottom = useRef<HTMLDivElement>(null)
  const results = useMemo(() => {
    const m = new Map<string, string>()
    for (const e of events) for (const r of e.tool_results) if (r.call_id) m.set(r.call_id, r.result)
    return m
  }, [events])

  useEffect(() => {
    if (running) bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [events.length, running])

  const rows = events.flatMap((e, i) => {
    if (!e.agent) return []
    const look = AGENTS[e.agent]
    const depth = Math.max(0, e.chain.length - 1)
    const style = { ['--ink' as string]: look.color, ['--tint' as string]: look.tint, ['--depth' as string]: depth }
    const key = `${e.run_id}-${i}`

    if (e.step_type === 'task_received') {
      const from = e.chain.length > 1 ? AGENTS[e.chain[e.chain.length - 2]] : null
      return [
        <div key={key} className="row row--handoff" style={style}>
          <div className="handoff__route">
            {from ? (
              <>
                <span style={{ color: from.color }}>{from.title}</span>
                <span className="handoff__arrow">⟶</span>
                <span style={{ color: look.color }}>{look.title}</span>
              </>
            ) : (
              <>
                <span className="muted">The desk</span>
                <span className="handoff__arrow">⟶</span>
                <span style={{ color: look.color }}>{look.title}</span>
              </>
            )}
          </div>
          {from && <p className="handoff__note">“{e.said}”</p>}
        </div>,
      ]
    }

    if (e.step_type === 'model_response') {
      const calls = e.tools_called.filter((c) => !HIDDEN_TOOLS.has(c.tool))
      const refusedAsks = e.tools_called.filter(
        (c) => c.tool === 'ask_teammate' && /refused|error/i.test(results.get(c.call_id ?? '') ?? ''),
      )
      if (!e.said && calls.length === 0 && refusedAsks.length === 0) return []
      return [
        <div key={key} className="row row--speech" style={style}>
          <Seal agent={e.agent} size={30} />
          <div className="speech">
            <span className="speech__who">{look.title}</span>
            {e.said && <p className="speech__text">{e.said}</p>}
            {calls.length > 0 && (
              <div className="chips">
                {calls.map((c, j) => (
                  <details key={j} className="chip">
                    <summary>
                      <span className="chip__label">{TOOL_LABELS[c.tool] ?? c.tool}</span>
                      {argSummary(c) && <span className="chip__args">{argSummary(c)}</span>}
                    </summary>
                    <div className="chip__body">
                      <code className="chip__tool">{c.tool}</code>
                      <pre>{results.has(c.call_id ?? '') ? prettyResult(results.get(c.call_id ?? '')!) : 'waiting for result…'}</pre>
                    </div>
                  </details>
                ))}
              </div>
            )}
            {refusedAsks.map((c, j) => (
              <p key={j} className="speech__refused">Hand-off to {String(c.args.teammate)} was refused: {results.get(c.call_id ?? '')}</p>
            ))}
          </div>
        </div>,
      ]
    }

    if (e.step_type === 'final_answer' && e.output) {
      if (depth === 0) {
        const d = e.output as TicketDecision
        return [
          <div key={key} className="row row--verdict" style={style}>
            <Seal agent="boss" size={36} state="done" />
            <div>
              <span className="speech__who">The Boss’s call · <em>{d.outcome.replaceAll('_', ' ')}</em></span>
              <p className="verdict__text">{d.summary}</p>
            </div>
          </div>,
        ]
      }
      const r = e.output as AgentReport
      const to = AGENTS[e.chain[e.chain.length - 2]]
      return [
        <div key={key} className="row row--report" style={style}>
          <Seal agent={e.agent} size={30} state="done" />
          <div className="speech">
            <span className="speech__who">
              {look.title} reports back to <span style={{ color: to.color }}>{to.title}</span>
            </span>
            <p className="speech__text">{r.summary}</p>
          </div>
        </div>,
      ]
    }

    if (e.step_type === 'error') {
      return [
        <div key={key} className="row row--error" style={style}>
          <strong>{look.title} hit a problem:</strong> {e.said}
        </div>,
      ]
    }
    return []
  })

  return (
    <div className="feed">
      {rows}
      {running && (
        <div className="row row--typing">
          <span className="dots"><i /><i /><i /></span> the team is working…
        </div>
      )}
      <div ref={bottom} />
    </div>
  )
}
