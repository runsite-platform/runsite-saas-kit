export interface PollOptions {
  attempts?: number
  intervalMs?: number
  signal?: AbortSignal
}

export interface PollResult<T> {
  value: T | null
  done: boolean
  attempts: number
}

const DEFAULT_ATTEMPTS = 10
const DEFAULT_INTERVAL_MS = 2000

function abortError(): DOMException {
  return new DOMException('Polling aborted', 'AbortError')
}

function wait(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(abortError())
      return
    }
    const handleAbort = () => {
      clearTimeout(timer)
      reject(abortError())
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', handleAbort)
      resolve()
    }, milliseconds)
    signal?.addEventListener('abort', handleAbort, { once: true })
  })
}

export async function pollUntil<T>(
  fetchValue: () => Promise<T>,
  isDone: (value: T) => boolean,
  { attempts = DEFAULT_ATTEMPTS, intervalMs = DEFAULT_INTERVAL_MS, signal }: PollOptions = {},
): Promise<PollResult<T>> {
  let lastValue: T | null = null
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    if (attempt > 1) {
      await wait(intervalMs, signal)
    }
    try {
      lastValue = await fetchValue()
    } catch (error) {
      if (signal?.aborted) throw error
      continue
    }
    if (isDone(lastValue)) {
      return { value: lastValue, done: true, attempts: attempt }
    }
  }
  return { value: lastValue, done: false, attempts }
}
