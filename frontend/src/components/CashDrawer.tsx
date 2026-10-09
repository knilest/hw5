import { useEffect, useRef, useState } from 'react'
import { money } from '../agents'
import type { Cash } from '../types'

/** Rolls a number from its old value to the new one, like an adding machine. */
function useRollingNumber(target: number, ms = 1100) {
  const [shown, setShown] = useState(target)
  const current = useRef(target) // what's on screen right now, so an interrupted roll resumes smoothly
  useEffect(() => {
    const start = performance.now()
    const begin = current.current
    let frame = 0
    const tick = (now: number) => {
      // rAF timestamps can be slightly earlier than `start`; clamp to [0, 1]
      const t = Math.min(1, Math.max(0, (now - start) / ms))
      const eased = 1 - Math.pow(1 - t, 3)
      current.current = begin + (target - begin) * eased
      setShown(current.current)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    // Background tabs throttle animation frames; make sure we land on the exact figure.
    const snap = setTimeout(() => {
      cancelAnimationFrame(frame)
      current.current = target
      setShown(target)
    }, ms + 150)
    return () => {
      cancelAnimationFrame(frame)
      clearTimeout(snap)
    }
  }, [target, ms])
  return shown
}

const KIND_LABEL: Record<string, string> = { invoice: 'Vendor invoice', rent: 'Rent', purchase_order: 'Purchase order' }

export function CashDrawer({ cash }: { cash: Cash | null }) {
  const balance = cash?.balance ?? 0
  const shown = useRollingNumber(balance)
  const [drop, setDrop] = useState<{ amount: number; key: number } | null>(null)
  const last = useRef<number | null>(null)

  useEffect(() => {
    if (cash == null) return
    if (last.current != null && cash.balance < last.current) {
      setDrop({ amount: last.current - cash.balance, key: Date.now() })
    }
    last.current = cash.balance
  }, [cash])

  if (!cash) return <div className="drawer drawer--loading">Opening the cash drawer…</div>

  // Share of today's cash already spoken for by pending requests (capped at 100%).
  const committed = Math.min(1, cash.pending_amount / Math.max(cash.balance, 1))
  const short = cash.balance_if_all_pending_approved < 0

  return (
    <section className="drawer">
      <span className="eyebrow">Checking · as of {cash.as_of}</span>
      <div className="drawer__balance">
        {money(shown)}
        {drop && (
          <span key={drop.key} className="drawer__drop">
            −{money(drop.amount)}
          </span>
        )}
      </div>
      <div className="drawer__meter" aria-label="cash committed to pending requests">
        <span className={`drawer__fill ${short ? 'drawer__fill--short' : ''}`} style={{ width: `${committed * 100}%` }} />
      </div>
      <p className="drawer__note">
        {cash.pending_requests === 0 ? (
          'Nothing waiting to be paid.'
        ) : (
          <>
            {money(cash.pending_amount)} waiting on {cash.pending_requests} approval{cash.pending_requests > 1 ? 's' : ''}.{' '}
            {short ? (
              <strong className="warn">That’s {money(-cash.balance_if_all_pending_approved)} more than we have.</strong>
            ) : (
              <>If all are approved: {money(cash.balance_if_all_pending_approved)}.</>
            )}
          </>
        )}
      </p>
      <p className="drawer__fineprint">No sales come in this term. Cash only goes out.</p>

      {cash.payments.length > 0 && (
        <div className="ledger">
          <span className="eyebrow">Paid out</span>
          {cash.payments.map((p) => (
            <div key={p.id} className="receipt">
              <span>{KIND_LABEL[p.kind] ?? p.kind} #{p.ref_id}</span>
              <span className="receipt__amt">−{money(p.amount)}</span>
              <span className="receipt__by">approved by {p.approved_by} · {p.paid_at}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
