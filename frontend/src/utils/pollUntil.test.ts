import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { pollUntil } from '@/utils/pollUntil'

describe('pollUntil', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('stops as soon as the condition is met', async () => {
    const responses = ['free', 'free', 'pro']
    let callIndex = 0
    const fetchValue = vi.fn(async () => responses[Math.min(callIndex++, responses.length - 1)])

    const resultPromise = pollUntil(fetchValue, (plan) => plan === 'pro', { attempts: 10, intervalMs: 2000 })
    await vi.advanceTimersByTimeAsync(4000)

    await expect(resultPromise).resolves.toEqual({ value: 'pro', done: true, attempts: 3 })
    expect(fetchValue).toHaveBeenCalledTimes(3)
  })

  it('gives up after ten attempts by default', async () => {
    const fetchValue = vi.fn(async () => 'free')

    const resultPromise = pollUntil(fetchValue, (plan) => plan === 'pro')
    await vi.advanceTimersByTimeAsync(2000 * 9)

    await expect(resultPromise).resolves.toEqual({ value: 'free', done: false, attempts: 10 })
    expect(fetchValue).toHaveBeenCalledTimes(10)
  })

  it('waits the interval between attempts', async () => {
    const fetchValue = vi.fn(async () => 'free')

    const resultPromise = pollUntil(fetchValue, () => false, { attempts: 2, intervalMs: 2000 })
    await vi.advanceTimersByTimeAsync(0)
    expect(fetchValue).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1999)
    expect(fetchValue).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(fetchValue).toHaveBeenCalledTimes(2)

    await expect(resultPromise).resolves.toMatchObject({ done: false, attempts: 2 })
  })

  it('counts failed requests toward the cap', async () => {
    const fetchValue = vi.fn(async (): Promise<string> => {
      throw new Error('offline')
    })

    const resultPromise = pollUntil(fetchValue, () => true, { attempts: 3, intervalMs: 2000 })
    await vi.advanceTimersByTimeAsync(4000)

    await expect(resultPromise).resolves.toEqual({ value: null, done: false, attempts: 3 })
    expect(fetchValue).toHaveBeenCalledTimes(3)
  })

  it('rejects with AbortError when aborted between attempts', async () => {
    const controller = new AbortController()
    const fetchValue = vi.fn(async () => 'free')

    const resultPromise = pollUntil(fetchValue, () => false, { signal: controller.signal })
    const assertion = expect(resultPromise).rejects.toMatchObject({ name: 'AbortError' })
    await vi.advanceTimersByTimeAsync(0)
    controller.abort()
    await assertion

    expect(fetchValue).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })
})
