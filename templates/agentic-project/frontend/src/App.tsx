import { ConnectionCard } from './components/ConnectionCard'
import { HealthCard } from './components/HealthCard'
import { useConnectionCheck } from './hooks/useConnectionCheck'
import { useHealthStatus } from './hooks/useHealthStatus'

/**
 * Root page: API health, checked on load, and the on-demand fixture connection check.
 *
 * Data comes from hooks; the cards only render it. Add a page section the same way: a hook in
 * `hooks/` that calls `api/client.ts`, and a presentational component in `components/`.
 */
export default function App() {
  const { health, isLoading, errorMessage: healthError, refreshHealth } = useHealthStatus()
  const {
    connection,
    isChecking,
    errorMessage: connectionError,
    startConnectionCheck,
  } = useConnectionCheck()

  return (
    <div className="app">
      <header className="app-header">
        <h1>Agentic Project Template</h1>
      </header>

      <main className="app-main">
        <HealthCard
          health={health}
          isLoading={isLoading}
          errorMessage={healthError}
          onRetry={refreshHealth}
        />
        <ConnectionCard
          connection={connection}
          isChecking={isChecking}
          errorMessage={connectionError}
          onRunCheck={startConnectionCheck}
        />
      </main>
    </div>
  )
}
