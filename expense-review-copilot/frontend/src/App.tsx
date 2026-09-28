import { useEffect, useState } from 'react'
import {
  AgentResult,
  checkHealth,
  ConnectionOutput,
  HealthResponse,
  runConnectionCheck,
} from './api/client'
import './App.css'

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [connection, setConnection] = useState<AgentResult<ConnectionOutput> | null>(null)
  const [isChecking, setIsChecking] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)

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

  function checkConnection() {
    setIsChecking(true)
    setConnectionError(null)
    setConnection(null)
    runConnectionCheck()
      .then((data) => {
        setConnection(data)
      })
      .catch((err) => {
        setConnectionError(err instanceof Error ? err.message : 'Unknown error')
      })
      .finally(() => {
        setIsChecking(false)
      })
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Expense Review Copilot</h1>
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

        <section className="card">
          <h2>Agent Connection (fixture)</h2>

          {isChecking && <p className="status loading">Running…</p>}

          {connectionError && (
            <p className="status error">
              Connection check failed: <code>{connectionError}</code>
            </p>
          )}

          {!isChecking && !connectionError && connection && (
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
            <button className="retry-btn" onClick={checkConnection}>
              Run check
            </button>
          )}
        </section>
      </main>
    </div>
  )
}
