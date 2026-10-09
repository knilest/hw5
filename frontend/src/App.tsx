import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, API_BASE } from './api'
import { money, prettyDate, TICKET_TYPE_LABELS } from './agents'
import type { AgentEvent, BoardItem, Cash, RunInfo, Ticket } from './types'
import { AgentRoster } from './components/AgentRoster'
import { CashDrawer } from './components/CashDrawer'
import { InTray } from './components/InTray'
import { LiveFeed } from './components/LiveFeed'
import { RunSummary } from './components/RunSummary'
import { TicketRail } from './components/TicketRail'

const POLL_MS = 1200

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [board, setBoard] = useState<BoardItem[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  // ?ticket=101 opens the desk on that ticket (handy for links and screenshots).
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const t = Number(new URLSearchParams(location.search).get('ticket'))
    return Number.isFinite(t) && t > 0 ? t : null
  })
  const [activeRun, setActiveRun] = useState<RunInfo | null>(null)
  const [signer, setSigner] = useState(() => localStorage.getItem('cc-signer') ?? '')
  const [busyItem, setBusyItem] = useState<number | null>(null)
  const [itemErrors, setItemErrors] = useState<Record<number, string>>({})
  const [banner, setBanner] = useState<{ tone: 'ok' | 'bad'; text: string } | null>(null)
  const [offline, setOffline] = useState<string | null>(null)

  const loadAll = useCallback(async () => {
    try {
      const [t, e, b, c] = await Promise.all([api.tickets(), api.events(), api.board(), api.cash()])
      setTickets(t)
      setEvents(e)
      setBoard(b)
      setCash(c)
      setOffline(null)
      setSelectedId((cur) => cur ?? t[0]?.id ?? null)
    } catch (err) {
      setOffline((err as Error).message)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // If the backend wasn't up yet, keep knocking until it answers.
  useEffect(() => {
    if (!offline) return
    const id = setInterval(loadAll, 3000)
    return () => clearInterval(id)
  }, [offline, loadAll])

  useEffect(() => localStorage.setItem('cc-signer', signer), [signer])

  const fullPage = new URLSearchParams(location.search).has('full')
  useEffect(() => {
    if (selectedId != null) history.replaceState(null, '', `?ticket=${selectedId}${fullPage ? '&full=1' : ''}`)
  }, [selectedId, fullPage])

  // While a run is going, keep refreshing so the floor fills in live.
  const anyRunning = activeRun?.status === 'running' || tickets.some((t) => t.running)
  useEffect(() => {
    if (!anyRunning) return
    const id = setInterval(async () => {
      await loadAll()
      if (activeRun?.status === 'running') {
        const r = await api.run(activeRun.run_id).catch(() => null)
        if (r && r.status !== 'running') {
          setActiveRun(r)
          await loadAll()
          setBanner(
            r.status === 'done'
              ? {
                  tone: 'ok',
                  text: `Ticket ${r.ticket_id} is back from the team. The Boss’s call: ${r.decision?.outcome.replaceAll('_', ' ')}${
                    r.decision?.human_actions_needed.length ? '. Your signature is needed in the in-tray.' : '.'
                  }`,
                }
              : { tone: 'bad', text: `Ticket ${r.ticket_id} run failed: ${r.error}` },
          )
        }
      }
    }, POLL_MS)
    return () => clearInterval(id)
  }, [anyRunning, activeRun, loadAll])

  const selected = tickets.find((t) => t.id === selectedId) ?? null

  // Events from the most recent run of the selected ticket.
  const runEvents = useMemo(() => {
    const mine = events.filter((e) => e.ticket_id === selectedId && e.run_id)
    const lastRun = mine.at(-1)?.run_id
    return mine.filter((e) => e.run_id === lastRun)
  }, [events, selectedId])

  const selectedRunning = !!selected?.running || (activeRun?.status === 'running' && activeRun.ticket_id === selectedId)
  const finished = runEvents.some((e) => e.step_type === 'final_answer' && e.chain.length === 1)

  async function startRun() {
    if (!selected) return
    setBanner(null)
    try {
      const run = await api.runTicket(selected.id)
      setActiveRun(run)
      await loadAll()
    } catch (err) {
      setBanner({ tone: 'bad', text: (err as Error).message })
    }
  }

  async function approve(item: BoardItem) {
    setBusyItem(item.id)
    setItemErrors((e) => ({ ...e, [item.id]: '' }))
    try {
      const r = await api.approve(item.id, signer.trim())
      setBanner(
        r.amount != null
          ? { tone: 'ok', text: `Paid ${money(r.amount)}. Checking is now ${money(r.new_balance)}.` }
          : { tone: 'ok', text: `Approved: ${item.title}.` },
      )
    } catch (err) {
      setItemErrors((e) => ({ ...e, [item.id]: (err as Error).message }))
    } finally {
      setBusyItem(null)
      loadAll()
    }
  }

  async function reject(item: BoardItem) {
    setBusyItem(item.id)
    try {
      await api.reject(item.id, signer.trim())
      setBanner({ tone: 'ok', text: `Rejected: ${item.title}.` })
    } catch (err) {
      setItemErrors((e) => ({ ...e, [item.id]: (err as Error).message }))
    } finally {
      setBusyItem(null)
      loadAll()
    }
  }

  async function reset() {
    if (!confirm('Reset the shop to the original database? The board and payments are cleared; the audit trail is kept.')) return
    try {
      await api.reset()
      setActiveRun(null)
      setItemErrors({})
      setBanner({ tone: 'ok', text: 'Fresh start: the shop is back to its original books.' })
      await loadAll()
    } catch (err) {
      setBanner({ tone: 'bad', text: (err as Error).message })
    }
  }

  return (
    <div className={`app ${fullPage ? 'full-page' : ''}`}>
      <header className="masthead">
        <div className="masthead__brand">
          <img src="/seal.svg" alt="" width={46} height={46} />
          <div>
            <h1>Campus Customs</h1>
            <p className="masthead__sub">The Desk · Chapel Street shop</p>
          </div>
        </div>
        <div className="masthead__date">{cash ? prettyDate(cash.as_of) : '…'}</div>
        <div className="masthead__tools">
          <label className="signer">
            <span>Signing as</span>
            <input value={signer} onChange={(e) => setSigner(e.target.value)} placeholder="your name" />
          </label>
          <button className="btn btn--quiet" onClick={reset} disabled={anyRunning}>Reset the shop</button>
        </div>
      </header>

      {offline && <div className="banner banner--bad">{offline} (Start it from backend/: <code>uvicorn main:app --reload --port 8000</code>; looking for {API_BASE}.)</div>}
      {banner && (
        <div className={`banner banner--${banner.tone}`} onClick={() => setBanner(null)}>
          {banner.text}
        </div>
      )}

      <main className="layout">
        <TicketRail tickets={tickets} board={board} selectedId={selectedId} onSelect={setSelectedId} />

        <section className="floor">
          {selected ? (
            <>
              <div className="ticket-card">
                <div className="ticket-card__top">
                  <span className="eyebrow">Ticket {selected.id} · {TICKET_TYPE_LABELS[selected.type] ?? selected.type}</span>
                  <span className={`stamp stamp--${selectedRunning ? 'running' : selected.state} stamp--big`}>
                    {selectedRunning ? 'In progress' : selected.state === 'resolved' ? 'Resolved' : 'Open'}
                  </span>
                </div>
                <h2 className="ticket-card__subject">{selected.subject}</h2>
                <p className="ticket-card__from">from <strong>{selected.requester}</strong></p>
                <blockquote className="ticket-card__note">{selected.notes?.split('\n')[0]}</blockquote>
                <dl className="ticket-card__facts">
                  {selected.sku && <><dt>Item</dt><dd>{selected.sku} · size {selected.size} · qty {selected.qty}</dd></>}
                  {selected.lease_id && <><dt>Lease</dt><dd>#{selected.lease_id}</dd></>}
                  {selected.invoice_id && <><dt>Invoice</dt><dd>#{selected.invoice_id}</dd></>}
                </dl>
                <button
                  className="btn btn--primary"
                  onClick={startRun}
                  disabled={anyRunning || selected.state === 'resolved'}
                >
                  {selectedRunning ? 'The team is on it…' : selected.state === 'resolved' ? 'Resolved' : anyRunning ? 'Another ticket is running' : 'Send to the team'}
                </button>
              </div>

              <AgentRoster events={runEvents} running={selectedRunning} />

              <div className="floor__feed">
                <h3 className="section-title section-title--small">On the floor</h3>
                {runEvents.length === 0 ? (
                  <p className="feed__empty">
                    Quiet for now. Press <em>Send to the team</em> and the Boss will pick this ticket up. You’ll see every hand-off and lookup here as it happens.
                  </p>
                ) : (
                  <LiveFeed events={runEvents} running={selectedRunning} />
                )}
              </div>

              {finished && !selectedRunning && <RunSummary events={runEvents} />}
            </>
          ) : (
            <p className="feed__empty">Loading tickets…</p>
          )}
        </section>

        <aside className="side">
          <CashDrawer cash={cash} />
          <InTray
            items={board}
            selectedTicket={selectedId}
            signer={signer.trim()}
            busyId={busyItem}
            errors={itemErrors}
            onApprove={approve}
            onReject={reject}
          />
        </aside>
      </main>

      <footer className="colophon">
        Five agents, one shared ledger, and a human who signs every dollar.
      </footer>
    </div>
  )
}
