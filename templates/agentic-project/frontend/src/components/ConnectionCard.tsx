import { AgentResult, ConnectionOutput } from '../api/client'

/** Props for {@link ConnectionCard}. */
export interface ConnectionCardProps {
  connection: AgentResult<ConnectionOutput> | null
  isChecking: boolean
  errorMessage: string | null
  onRunCheck: () => void
}

/**
 * Show the fixture connection check's result and provenance, with a button to run it.
 *
 * @param props - Result to display and the run callback; this component fetches nothing.
 */
export function ConnectionCard({
  connection,
  isChecking,
  errorMessage,
  onRunCheck,
}: ConnectionCardProps) {
  return (
    <section className="card">
      <h2>Agent Connection (fixture)</h2>

      {isChecking && <p className="status loading">Running…</p>}

      {errorMessage && (
        <p className="status error">
          Connection check failed: <code>{errorMessage}</code>
        </p>
      )}

      {!isChecking && !errorMessage && connection && (
        <dl className="health-details">
          <dt>Marker</dt>
          <dd className="ok">{connection.output.marker}</dd>

          <dt>Provider</dt>
          <dd>{connection.provider}</dd>

          <dt>Model</dt>
          <dd>{connection.model_id}</dd>

          <dt>Prompt</dt>
          <dd>v{connection.prompt_version}</dd>
        </dl>
      )}

      {!isChecking && (
        <button className="retry-btn" onClick={onRunCheck}>
          Run check
        </button>
      )}
    </section>
  )
}
