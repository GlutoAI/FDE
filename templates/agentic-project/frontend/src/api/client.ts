/**
 * Typed calls to the backend API.
 *
 * Every interface mirrors a backend Pydantic model by hand; there is no code generation, so a
 * backend contract change needs the matching edit here.
 */

/** Same-origin prefix: Vite (dev) and nginx (Docker) strip it and forward to the backend. */
const BASE_URL = '/api'

/** Application and database status. Mirrors `HealthResponse` in `app/routers/health.py`. */
export interface HealthResponse {
  status: 'ok' | 'error'
  db: 'connected' | 'disconnected'
  /** Safe failure code, present only when `status` is `error`. */
  detail?: string
}

/** Structured probe output. Mirrors `ConnectionOutput` in `app/agents/connection/models.py`. */
export interface ConnectionOutput {
  status: 'ok'
  marker: 'CONNECTION_OK'
}

/** Validated agent output plus provenance. Mirrors `AgentResult[OutputT]` in `app/llm/contracts.py`. */
export interface AgentResult<TOutput> {
  status: 'ok'
  output: TOutput
  provider: 'fixture' | 'openai' | 'anthropic'
  model_id: string
  prompt_version: number
  prompt_sha256: string
  /** Null for the fixture model and whenever the provider reported no usage. */
  input_tokens: number | null
  output_tokens: number | null
}

/**
 * Fetch the API and database status.
 *
 * @returns The backend's status. A failed request still resolves, with `status: 'error'` and
 *   the backend's safe code (or the HTTP status) in `detail`.
 * @throws TypeError when the API cannot be reached at all (network error).
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${BASE_URL}/health`)
  if (!response.ok) {
    const detail = readSafeDetail(await readJsonBody(response)) ?? `HTTP ${response.status}`
    return { status: 'error', db: 'disconnected', detail }
  }
  return (await response.json()) as HealthResponse
}

/**
 * Run the fixture connection agent once; the backend never makes a paid request for this.
 *
 * @returns The validated probe output and its provenance.
 * @throws Error carrying the backend's safe error code, or the HTTP status when there is none.
 */
export async function runConnectionCheck(): Promise<AgentResult<ConnectionOutput>> {
  const response = await fetch(`${BASE_URL}/diagnostics/connection`, { method: 'POST' })
  if (!response.ok) {
    const detail = readSafeDetail(await readJsonBody(response))
    throw new Error(detail ?? `HTTP ${response.status}`)
  }
  return (await response.json()) as AgentResult<ConnectionOutput>
}

/**
 * Turn anything thrown by a request into a message fit to show the user.
 *
 * @param error - The caught value; not necessarily an `Error`.
 * @returns The error's message, or a generic fallback.
 */
export function formatErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error'
}

/** Parse a response body as JSON, or return null when it is not JSON (e.g. a proxy error page). */
async function readJsonBody(response: Response): Promise<unknown> {
  return response.json().catch(() => null)
}

/** Return the body's `detail` when it is a string: the backend's safe code, never a stack trace. */
function readSafeDetail(body: unknown): string | undefined {
  if (typeof body !== 'object' || body === null || !('detail' in body)) {
    return undefined
  }
  return typeof body.detail === 'string' ? body.detail : undefined
}
