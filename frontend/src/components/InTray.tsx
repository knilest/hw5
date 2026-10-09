import { useState } from 'react'
import { AGENTS, money } from '../agents'
import type { AgentName, BoardItem } from '../types'
import { Seal } from './Seal'

const KIND: Record<BoardItem['kind'], { label: string; approve: (i: BoardItem) => string }> = {
  payment: { label: 'Payment', approve: (i) => `Approve & pay ${money(i.amount)}` },
  purchase_order: { label: 'Purchase order', approve: (i) => `Approve & pay ${money(i.amount)}` },
  discount: { label: 'Discount', approve: () => 'Approve price' },
  customer_message: { label: 'Customer note', approve: () => 'Approve draft' },
}

const STAMP: Record<string, string> = { executed: 'Paid', approved: 'Approved', rejected: 'Rejected' }

interface Props {
  items: BoardItem[]
  selectedTicket: number | null
  signer: string
  busyId: number | null
  errors: Record<number, string>
  onApprove: (item: BoardItem) => void
  onReject: (item: BoardItem) => void
}

function Warnings({ item }: { item: BoardItem }) {
  const d = item.details
  const out: string[] = []
  if (item.kind === 'purchase_order' && d.blocked_by_open_invoices?.length && item.status === 'pending') {
    out.push(`Vendor won’t ship until invoice ${d.blocked_by_open_invoices.join(', ')} is paid.`)
  }
  if ((item.kind === 'payment' || item.kind === 'purchase_order') && d.covered_by_cash === false && item.status === 'pending') {
    out.push('Not enough cash when this was requested.')
  }
  if (item.kind === 'payment' && d.overdue && item.status === 'pending') out.push(`Overdue since ${d.due_date}.`)
  return out.length ? <ul className="item__warn">{out.map((w) => <li key={w}>{w}</li>)}</ul> : null
}

function Details({ item }: { item: BoardItem }) {
  const d = item.details
  if (item.kind === 'customer_message') {
    return (
      <details className="letter">
        <summary>Read the draft to {d.to}</summary>
        <div className="letter__paper">
          <p className="letter__subject">{d.subject}</p>
          {String(d.body).split('\n').map((line, i) => <p key={i}>{line}</p>)}
          <p className="letter__note">Draft only. Approving doesn’t send it.</p>
        </div>
      </details>
    )
  }
  if (item.kind === 'discount') {
    return (
      <p className="item__line">
        {d.qty} × {d.sku} at <strong>{money(d.unit_price)}</strong> (list {money(d.list_price)}, {d.discount_pct}% off) ·
        profit {money(d.order_profit)}
      </p>
    )
  }
  if (item.kind === 'purchase_order') {
    return (
      <p className="item__line">
        {d.qty} × {d.item_name} ({d.size}) from {d.vendor_name} · {d.lead_days}-day lead
      </p>
    )
  }
  return <p className="item__line">To {d.payee} · due {d.due_date}</p>
}

/** The in-tray: everything the agents prepared that needs a human's signature. */
export function InTray({ items, selectedTicket, signer, busyId, errors, onApprove, onReject }: Props) {
  const [scope, setScope] = useState<'ticket' | 'all'>('all')
  const shown = items
    .filter((i) => scope === 'all' || i.ticket_id === selectedTicket)
    .sort((a, b) => Number(isOpen(b)) - Number(isOpen(a)) || a.id - b.id)
  const waiting = items.filter(isOpen).length

  return (
    <section className="tray">
      <div className="tray__head">
        <div>
          <h2 className="section-title">In-tray</h2>
          <p className="section-sub">{waiting ? `${waiting} waiting for your signature` : 'Nothing waiting for you'}</p>
        </div>
        <div className="toggle">
          <button className={scope === 'all' ? 'on' : ''} onClick={() => setScope('all')}>All</button>
          <button className={scope === 'ticket' ? 'on' : ''} onClick={() => setScope('ticket')}>This ticket</button>
        </div>
      </div>

      {shown.length === 0 && <p className="tray__empty">The agents haven’t put anything here yet.</p>}

      {shown.map((item) => {
        const open = isOpen(item)
        const who = (item.created_by in AGENTS ? item.created_by : 'boss') as AgentName
        return (
          <article key={item.id} className={`item item--${item.kind} item--${item.status} ${item.ticket_id === selectedTicket ? 'item--here' : ''}`}>
            <header className="item__head">
              <span className="item__kind">{KIND[item.kind].label}</span>
              <span className="item__ticket">ticket {item.ticket_id} · #{item.id}</span>
            </header>
            <div className="item__title">
              <Seal agent={who} size={22} />
              <span>{item.title}</span>
            </div>
            <Details item={item} />
            <Warnings item={item} />
            {errors[item.id] && <p className="item__error">{errors[item.id]}</p>}
            {open ? (
              <div className="item__actions">
                <button className="btn btn--approve" disabled={!signer || busyId === item.id} onClick={() => onApprove(item)}>
                  {busyId === item.id ? 'Signing…' : KIND[item.kind].approve(item)}
                </button>
                <button className="btn btn--quiet" disabled={!signer || busyId === item.id} onClick={() => onReject(item)}>
                  Reject
                </button>
              </div>
            ) : (
              <p className="item__decided">
                {item.decided_by ? `${STAMP[item.status] ?? item.status} by ${item.decided_by}` : ''}
              </p>
            )}
            {!open && <span className={`item-stamp item-stamp--${item.status}`}>{STAMP[item.status] ?? item.status}</span>}
          </article>
        )
      })}
      {!signer && waiting > 0 && <p className="tray__hint">Sign in at the top (“Signing as”) to approve.</p>}
    </section>
  )
}

function isOpen(i: BoardItem) {
  return i.status === 'pending' || i.status === 'draft'
}
