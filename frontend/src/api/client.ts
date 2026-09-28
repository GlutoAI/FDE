const BASE_URL = '/api'  // proxied to http://localhost:8000 by Vite

export interface HealthResponse {
  status: 'ok' | 'error'
  db: 'connected' | 'disconnected'
  detail?: string
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    return { status: 'error', db: 'disconnected', ...body }
  }
  return res.json()
}
