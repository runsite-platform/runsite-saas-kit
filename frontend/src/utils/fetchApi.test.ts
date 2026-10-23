// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/utils/apiError'
import { onPlanUpgradeRequired } from '@/utils/apiEvents'
import { fetchApi } from '@/utils/fetchApi'
import { getAccessToken, setAccessToken, setRefreshHandler, setUnauthorizedHandler } from '@/utils/tokenStore'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function requestHeaders(fetchMock: ReturnType<typeof vi.fn>, callIndex: number): Record<string, string> {
  const init = fetchMock.mock.calls[callIndex][1] as RequestInit
  return init.headers as Record<string, string>
}

const unauthorizedBody = { error: { code: 'not_authenticated', message: 'Not authenticated' } }

describe('fetchApi', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken(null)
    setRefreshHandler(null)
    setUnauthorizedHandler(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('prefixes /api, sends the bearer token and parses JSON', async () => {
    setAccessToken('access-1')
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: 'ok' }))

    const result = await fetchApi<{ status: string }>('/health')

    expect(result).toEqual({ status: 'ok' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/health')
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.method).toBe('GET')
    expect(init.credentials).toBe('include')
    expect(requestHeaders(fetchMock, 0).Authorization).toBe('Bearer access-1')
  })

  it('omits the token when auth is false', async () => {
    setAccessToken('access-1')
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}))

    await fetchApi('/config/public', { auth: false })

    expect(requestHeaders(fetchMock, 0).Authorization).toBeUndefined()
  })

  it('serialises JSON bodies with a content type', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(201, { id: '1' }))

    await fetchApi('/orgs', { method: 'POST', body: { name: 'Acme' } })

    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.body).toBe(JSON.stringify({ name: 'Acme' }))
    expect(requestHeaders(fetchMock, 0)['Content-Type']).toBe('application/json')
  })

  it('sends form data without a JSON content type', async () => {
    const formData = new FormData()
    formData.append('name', 'logo.png')
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}))

    await fetchApi('/me/avatar', { method: 'PUT', formData })

    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.body).toBe(formData)
    expect(requestHeaders(fetchMock, 0)['Content-Type']).toBeUndefined()
  })

  it('returns undefined for 204 responses', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await expect(fetchApi('/orgs/1', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('refreshes once on 401 and retries with the new token', async () => {
    setAccessToken('expired')
    const refreshHandler = vi.fn().mockResolvedValueOnce('fresh-token')
    const unauthorizedHandler = vi.fn()
    setRefreshHandler(refreshHandler)
    setUnauthorizedHandler(unauthorizedHandler)
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, unauthorizedBody))
      .mockResolvedValueOnce(jsonResponse(200, { id: 'user-1' }))

    const result = await fetchApi<{ id: string }>('/me')

    expect(result).toEqual({ id: 'user-1' })
    expect(refreshHandler).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(requestHeaders(fetchMock, 1).Authorization).toBe('Bearer fresh-token')
    expect(getAccessToken()).toBe('fresh-token')
    expect(unauthorizedHandler).not.toHaveBeenCalled()
  })

  it('calls the unauthorized handler when the retry is still 401', async () => {
    const refreshHandler = vi.fn().mockResolvedValueOnce('fresh-token')
    const unauthorizedHandler = vi.fn()
    setRefreshHandler(refreshHandler)
    setUnauthorizedHandler(unauthorizedHandler)
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, unauthorizedBody))
      .mockResolvedValueOnce(jsonResponse(401, unauthorizedBody))

    const request = fetchApi('/me')

    await expect(request).rejects.toMatchObject({ status: 401, code: 'not_authenticated' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(refreshHandler).toHaveBeenCalledTimes(1)
    expect(unauthorizedHandler).toHaveBeenCalledTimes(1)
  })

  it('calls the unauthorized handler without retrying when refresh fails', async () => {
    const refreshHandler = vi.fn().mockResolvedValueOnce(null)
    const unauthorizedHandler = vi.fn()
    setRefreshHandler(refreshHandler)
    setUnauthorizedHandler(unauthorizedHandler)
    fetchMock.mockResolvedValueOnce(jsonResponse(401, unauthorizedBody))

    await expect(fetchApi('/me')).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(unauthorizedHandler).toHaveBeenCalledTimes(1)
  })

  it('treats a throwing refresh handler as a failed refresh', async () => {
    const refreshHandler = vi.fn().mockRejectedValueOnce(new Error('offline'))
    const unauthorizedHandler = vi.fn()
    setRefreshHandler(refreshHandler)
    setUnauthorizedHandler(unauthorizedHandler)
    fetchMock.mockResolvedValueOnce(jsonResponse(401, unauthorizedBody))

    await expect(fetchApi('/me')).rejects.toMatchObject({ status: 401 })
    expect(unauthorizedHandler).toHaveBeenCalledTimes(1)
  })

  it('does not refresh when auth is false', async () => {
    const refreshHandler = vi.fn()
    setRefreshHandler(refreshHandler)
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { error: { code: 'invalid_credentials', message: 'Bad' } }))

    await expect(fetchApi('/auth/login', { method: 'POST', body: {}, auth: false })).rejects.toMatchObject({
      code: 'invalid_credentials',
    })
    expect(refreshHandler).not.toHaveBeenCalled()
  })

  it('throws other 401 codes without refreshing or calling the unauthorized handler', async () => {
    setAccessToken('access-1')
    const refreshHandler = vi.fn()
    const unauthorizedHandler = vi.fn()
    setRefreshHandler(refreshHandler)
    setUnauthorizedHandler(unauthorizedHandler)
    fetchMock.mockResolvedValueOnce(
      jsonResponse(401, { error: { code: 'invalid_credentials', message: 'Wrong password' } }),
    )

    await expect(fetchApi('/me/password', { method: 'POST', body: {} })).rejects.toMatchObject({
      status: 401,
      code: 'invalid_credentials',
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(refreshHandler).not.toHaveBeenCalled()
    expect(unauthorizedHandler).not.toHaveBeenCalled()
  })

  it('emits plan-upgrade-required on 402 with that code', async () => {
    const listener = vi.fn()
    const unsubscribe = onPlanUpgradeRequired(listener)
    const details = { feature: 'analytics', required_plan: 'pro' }
    fetchMock.mockResolvedValueOnce(
      jsonResponse(402, { error: { code: 'plan_upgrade_required', message: 'Upgrade', details } }),
    )

    await expect(fetchApi('/orgs/1/overview/charts')).rejects.toMatchObject({ code: 'plan_upgrade_required' })
    expect(listener).toHaveBeenCalledWith(details)
    unsubscribe()
  })

  it('does not emit the upgrade event for other 402 codes', async () => {
    const listener = vi.fn()
    const unsubscribe = onPlanUpgradeRequired(listener)
    fetchMock.mockResolvedValueOnce(
      jsonResponse(402, { error: { code: 'plan_limit_reached', message: 'Limit', details: { limit: 'projects' } } }),
    )

    await expect(fetchApi('/orgs/1/projects', { method: 'POST', body: {} })).rejects.toMatchObject({
      code: 'plan_limit_reached',
    })
    expect(listener).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('wraps fetch failures in a network_error', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(fetchApi('/health')).rejects.toMatchObject({ status: 0, code: 'network_error' })
  })
})
