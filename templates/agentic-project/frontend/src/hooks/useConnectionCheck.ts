import { useCallback, useState } from 'react'
import {
  AgentResult,
  ConnectionOutput,
  formatErrorMessage,
  runConnectionCheck,
} from '../api/client'

/** State and actions returned by {@link useConnectionCheck}. */
export interface ConnectionCheck {
  /** Result of the last successful check, or null before the first one and after a failure. */
  connection: AgentResult<ConnectionOutput> | null
  isChecking: boolean
  /** The backend's safe error code from the last failed check. */
  errorMessage: string | null
  /** Run the fixture connection check once. */
  startConnectionCheck: () => void
}

/**
 * Run the fixture connection check on demand; nothing runs on mount.
 *
 * @returns The latest result, progress and error state, and the action that starts a check.
 */
export function useConnectionCheck(): ConnectionCheck {
  const [connection, setConnection] = useState<AgentResult<ConnectionOutput> | null>(null)
  const [isChecking, setIsChecking] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const startConnectionCheck = useCallback(() => {
    setIsChecking(true)
    setErrorMessage(null)
    setConnection(null)
    runConnectionCheck()
      .then(setConnection)
      .catch((error: unknown) => setErrorMessage(formatErrorMessage(error)))
      .finally(() => setIsChecking(false))
  }, [])

  return { connection, isChecking, errorMessage, startConnectionCheck }
}
