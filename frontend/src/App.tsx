import { useEffect, useState } from 'react'
import { checkHealth, HealthResponse } from './api/client'
import './App.css'

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function fetchHealth() {
    setLoading(true)
    setError(null)
    setHealth(null)
    checkHealth()
      .then((data) => {
        setHealth(data)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Unknown error')
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>FDE Interview App</h1>
      </header>

      <main className="app-main">
        <section className="card">
          <h2>API Health</h2>

          {loading && <p className="status loading">Checking…</p>}

          {error && (
            <p className="status error">
              Failed to reach API: <code>{error}</code>
            </p>
          )}

          {!loading && !error && health && (
            <dl className="health-details">
              <dt>Status</dt>
              <dd className={health.status === 'ok' ? 'ok' : 'error'}>
                {health.status}
              </dd>

              <dt>Database</dt>
              <dd className={health.db === 'connected' ? 'ok' : 'error'}>
                {health.db}
              </dd>

              {health.detail && (
                <>
                  <dt>Detail</dt>
                  <dd>{health.detail}</dd>
                </>
              )}
            </dl>
          )}

          {!loading && (
            <button className="retry-btn" onClick={fetchHealth}>
              Retry
            </button>
          )}
        </section>
      </main>
    </div>
  )
}
