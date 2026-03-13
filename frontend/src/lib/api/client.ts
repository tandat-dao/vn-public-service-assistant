const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

/** Stream chat response as SSE. Yields raw data strings from each `data: …` line. */
export async function* streamChat(
  sessionId: string,
  message: string,
  file?: File,
): AsyncGenerator<string> {
  const body = new FormData()
  body.append('session_id', sessionId)
  body.append('message', message)
  if (file) body.append('file', file)

  const res = await fetch(`${BASE}/api/v1/chat`, { method: 'POST', body })
  if (!res.ok || !res.body) throw new Error('Chat stream failed')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data === '[DONE]') return
        yield data
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
    upload: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return apiFetch<any>('/api/v1/documents/upload', { method: 'POST', body: fd, headers: {} })
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
