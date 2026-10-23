import { useCallback, useEffect, useEffectEvent, useState, type DependencyList } from 'react'

interface SettledQuery<T> {
  requestKey: string | null
  data: T | null
  error: unknown
}

export interface ApiQueryResult<T> {
  data: T | null
  error: unknown
  isLoading: boolean
  reload: () => void
}

export function useApiQuery<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  dependencies: DependencyList,
): ApiQueryResult<T> {
  const [reloadCounter, setReloadCounter] = useState(0)
  const [settled, setSettled] = useState<SettledQuery<T>>({ requestKey: null, data: null, error: null })
  const requestKey = JSON.stringify([...dependencies, reloadCounter])
  const runLoader = useEffectEvent((signal: AbortSignal) => loader(signal))

  useEffect(() => {
    const controller = new AbortController()
    runLoader(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setSettled({ requestKey, data, error: null })
      },
      (error: unknown) => {
        if (!controller.signal.aborted) setSettled({ requestKey, data: null, error })
      },
    )
    return () => controller.abort()
  }, [requestKey])

  const reload = useCallback(() => setReloadCounter((counter) => counter + 1), [])
  const isLoading = settled.requestKey !== requestKey
  return { data: settled.data, error: isLoading ? null : settled.error, isLoading, reload }
}
