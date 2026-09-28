const BASE_URL = '/api'  // proxied to http://localhost:8000 by Vite

export interface HealthResponse {
  status: 'ok' | 'error'
  db: 'connected' | 'disconnected'
  detail?: string
}

/** Structured probe output. Mirrors ConnectionOutput. */
export interface ConnectionOutput {
  status: 'ok'
  marker: 'CONNECTION_OK'
}

/** Validated agent output plus provenance. Mirrors AgentResult[OutputT]. */
export interface AgentResult<TOutput> {
  status: 'ok'
  output: TOutput
  provider: 'fixture' | 'openai' | 'anthropic'
  model_id: string
  prompt_version: number
  prompt_sha256: string
  input_tokens: number | null
  output_tokens: number | null
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    return { status: 'error', db: 'disconnected', ...body }
  }
  return res.json()
}

/** Run the fixture connection agent; throws with the backend's safe error code on failure. */
export async function runConnectionCheck(): Promise<AgentResult<ConnectionOutput>> {
  const res = await fetch(`${BASE_URL}/diagnostics/connection`, { method: 'POST' })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `HTTP ${res.status}`)
  }
  return res.json()
}
