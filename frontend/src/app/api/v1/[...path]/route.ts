import { NextRequest } from 'next/server'

const BACKEND_URL = 'http://localhost:8000'

async function handler(request: NextRequest, context: { params: { path: string[] } }) {
  const path = (await context.params).path.join('/')
  const url = `${BACKEND_URL}/api/v1/${path}`

  const init: RequestInit = {
    method: request.method,
    headers: {
      'Content-Type': request.headers.get('Content-Type') || 'application/json',
      'Accept': request.headers.get('Accept') || '*/*',
    },
  }

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.text()
  }

  const backendResponse = await fetch(url, { ...init, cache: 'no-store' })

  const isSSE = backendResponse.headers.get('content-type')?.includes('text/event-stream')

  if (isSSE) {
    return new Response(backendResponse.body, {
      status: backendResponse.status,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    })
  }

  const responseHeaders = new Headers()
  backendResponse.headers.forEach((value, key) => {
    if (key !== 'content-encoding') responseHeaders.set(key, value)
  })

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  })
}

export const GET = handler
export const POST = handler
export const PUT = handler
export const DELETE = handler