import { useCallback, useEffect, useState } from 'react'
import { checkHealth, formatErrorMessage, HealthResponse } from '../api/client'

/** State and actions returned by {@link useHealthStatus}. */
export interface HealthStatus {
  /** Latest status, or null while loading or after a network failure. */
  health: HealthResponse | null
  isLoading: boolean
  /** Set only when the API could not be reached; a 503 arrives as `health` instead. */
  errorMessage: string | null
  /** Discard the current status and fetch it again. */
  refreshHealth: () => void
}

/**
 * Fetch the API health once on mount and on every `refreshHealth` call.
 *
 * @returns The latest status, loading and error state, and the refresh action.
 */
export function useHealthStatus(): HealthStatus {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const refreshHealth = useCallback(() => {
    setIsLoading(true)
    setErrorMessage(null)
    setHealth(null)
    checkHealth()
      .then(setHealth)
      .catch((error: unknown) => setErrorMessage(formatErrorMessage(error)))
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    refreshHealth()
  }, [refreshHealth])

  return { health, isLoading, errorMessage, refreshHealth }
}
