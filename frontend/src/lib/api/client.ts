import type { DocumentUploadResponse, PipelineEvent } from '@/lib/types'

const BASE = process.env.NEXT_PUBLIC_API_URL_PUBLIC
  || process.env.NEXT_PUBLIC_API_URL
  || 'http://localhost:8000'

// Ngrok free tier intercepts preflight OPTIONS with a browser warning page unless this header is set.
const NGROK_HEADER: Record<string, string> = BASE.includes('ngrok')
  ? { 'ngrok-skip-browser-warning': 'true' }
  : {}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...NGROK_HEADER, ...init?.headers },
    ...init,
  })
  if (!res.ok) throw Object.assign(new Error(`API ${path} → ${res.status}`), { status: res.status })
  return res.json()
}

/**
 * Stream chat response as SSE.
 *
 * Yields raw data strings from each `data: …` line that does NOT carry a
 * `event: pipeline_event` type. Pipeline events are passed to the optional
 * `onPipelineEvent` callback instead of being yielded.
 *
 * Backward-compat: existing callers that don't pass `onPipelineEvent` receive
 * exactly the same text/metadata data strings as before. Pipeline event data
 * is silently discarded (never yielded) — it won't corrupt old parsers.
 */
export async function* streamChat(
  sessionId: string,
  message: string,
  imagePath?: string,
  citizenId?: string,
  onPipelineEvent?: (event: PipelineEvent) => void,
): AsyncGenerator<string> {
  const body: Record<string, string> = { session_id: sessionId, message }
  if (imagePath) body.image_path = imagePath
  if (citizenId) body.citizen_id = citizenId
  const res = await fetch(`${BASE}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...NGROK_HEADER },
    body: JSON.stringify(body),
  })
  if (!res.ok || !res.body) {
    throw Object.assign(
      new Error('Chat stream failed'),
      { status: res.status },
    )
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // Tracks the `event:` field of the SSE event currently being assembled.
  // Resets to null on each blank line (event boundary).
  let currentEventType: string | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line === '') {
        // Blank line = SSE event boundary: reset current event type
        currentEventType = null
      } else if (line.startsWith('event: ')) {
        currentEventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data === '[DONE]') return

        if (currentEventType === 'pipeline_event') {
          // Route to callback — never yield pipeline events as raw data
          if (onPipelineEvent) {
            try {
              onPipelineEvent(JSON.parse(data) as PipelineEvent)
            } catch { /* ignore malformed pipeline event */ }
          }
        } else {
          // Default SSE data (text chunk or metadata) — yield as before
          yield data
        }
      }
    }
  }
}

export const api = {
  procedures: {
    stats:  () => apiFetch<any>('/api/v1/procedures/stats'),
    list:   (p: Record<string, string>) =>
      apiFetch<any>(`/api/v1/procedures?${new URLSearchParams(p)}`),
    detail: (id: string) => apiFetch<any>(`/api/v1/procedures/${id}`),
  },
  faq: {
    list: (q: string, cat: string) =>
      apiFetch<any>(`/api/v1/faq?q=${encodeURIComponent(q)}&category=${cat}`),
  },
  submissions: {
    lookup: (maHoSo: string) => apiFetch<any>(`/api/v1/submissions/${maHoSo}`),
  },
  qualityIndex: {
    list: (p: Record<string, string>) =>
      apiFetch<any>(`/api/v1/quality-index?${new URLSearchParams(p)}`),
  },
  documents: {
    upload: (file: File, sessionId: string, citizenId?: string) => {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('session_id', sessionId)
      if (citizenId) fd.append('citizen_id', citizenId)
      return apiFetch<DocumentUploadResponse>(
        '/api/v1/documents/upload',
        { method: 'POST', body: fd, headers: {} },
      )
    },
  },
  forms: {
    submit: (body: {
      form_type: 'thuong-tru' | 'tam-tru' | 'xac-nhan'
      session_id: string
      submission_mode: 'manual' | 'ai'
      form_data: Record<string, string | undefined>
    }) =>
      apiFetch<{
        ma_ho_so: string
        form_type: string
        submitted_at: string
        status: string
        message: string
      }>('/api/v1/forms/submit', { method: 'POST', body: JSON.stringify(body) }),
  },
}
