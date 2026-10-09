import type { AgentEvent, BoardItem, Cash, RunInfo, Ticket } from './types'

// The FastAPI backend from Problem 7.
export const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}. Is uvicorn running?`)
  }
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, (body as { detail?: string }).detail ?? res.statusText)
  return body as T
}

export const api = {
  tickets: () => request<Ticket[]>('/api/tickets'),
  runTicket: (id: number) => request<RunInfo>(`/api/tickets/${id}/run`, { method: 'POST' }),
  run: (runId: string) => request<RunInfo>(`/api/runs/${runId}`),
  events: () => request<AgentEvent[]>('/api/events?since_last_reset=true&limit=1000'),
  board: () => request<BoardItem[]>('/api/board'),
  approve: (id: number, approvedBy: string, note = '') =>
    request<{ ok: boolean; new_balance?: number; amount?: number; item: BoardItem }>(
      `/api/board/${id}/approve`,
      { method: 'POST', body: JSON.stringify({ approved_by: approvedBy, note }) },
    ),
  reject: (id: number, decidedBy: string, note = '') =>
    request<{ ok: boolean; item: BoardItem }>(`/api/board/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: decidedBy, note }),
    }),
  cash: () => request<Cash>('/api/cash'),
  reset: () => request<{ ok: boolean }>('/api/reset', { method: 'POST' }),
  health: () => request<{ ok: boolean; running_ticket: number | null }>('/api/health'),
}
