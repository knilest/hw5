import { TICKET_TYPE_LABELS } from '../agents'
import type { BoardItem, Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  board: BoardItem[]
  selectedId: number | null
  onSelect: (id: number) => void
}

/** The ticket spike: each open request is a paper stub you can pull off the pile. */
export function TicketRail({ tickets, board, selectedId, onSelect }: Props) {
  return (
    <aside className="rail">
      <h2 className="section-title">On the spike</h2>
      <p className="section-sub">{tickets.filter((t) => t.state === 'open').length} open · {tickets.length} total</p>
      <ul className="stubs">
        {tickets.map((t) => {
          const waiting = board.filter((b) => b.ticket_id === t.id && (b.status === 'pending' || b.status === 'draft')).length
          const stamp = t.running ? 'running' : t.state
          return (
            <li key={t.id}>
              <button
                className={`stub stub--${stamp} ${selectedId === t.id ? 'stub--selected' : ''}`}
                onClick={() => onSelect(t.id)}
              >
                <span className="stub__no">No. {t.id}</span>
                <span className="stub__type">{TICKET_TYPE_LABELS[t.type] ?? t.type}</span>
                <span className="stub__subject">{t.subject}</span>
                <span className="stub__from">from {t.requester}</span>
                {waiting > 0 && <span className="stub__waiting">{waiting} awaiting you</span>}
                <span className={`stamp stamp--${stamp}`}>
                  {stamp === 'running' ? 'In progress' : stamp === 'resolved' ? 'Resolved' : 'Open'}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
