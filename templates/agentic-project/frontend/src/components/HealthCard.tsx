import { HealthResponse } from '../api/client'

/** Props for {@link HealthCard}. */
export interface HealthCardProps {
  health: HealthResponse | null
  isLoading: boolean
  errorMessage: string | null
  onRetry: () => void
}

/**
 * Show the API and database status, with a retry button once a check has finished.
 *
 * @param props - Status to display and the retry callback; this component fetches nothing.
 */
export function HealthCard({ health, isLoading, errorMessage, onRetry }: HealthCardProps) {
  return (
    <section className="card">
      <h2>API Health</h2>

      {isLoading && <p className="status loading">Checking…</p>}

      {errorMessage && (
        <p className="status error">
          Failed to reach API: <code>{errorMessage}</code>
        </p>
      )}

      {!isLoading && !errorMessage && health && (
        <dl className="health-details">
          <dt>Status</dt>
          <dd className={health.status === 'ok' ? 'ok' : 'error'}>{health.status}</dd>

          <dt>Database</dt>
          <dd className={health.db === 'connected' ? 'ok' : 'error'}>{health.db}</dd>

          {health.detail && (
            <>
              <dt>Detail</dt>
              <dd>{health.detail}</dd>
            </>
          )}
        </dl>
      )}

      {!isLoading && (
        <button className="retry-btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </section>
  )
}
