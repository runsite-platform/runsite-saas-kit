import { ApiError, apiErrorFromBody, networkError } from '@/utils/apiError'
import { emitPlanUpgradeRequired, type PlanUpgradeDetails } from '@/utils/apiEvents'
import { getAccessToken, getRefreshHandler, getUnauthorizedHandler, setAccessToken } from '@/utils/tokenStore'

export const API_BASE_URL = '/api'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface FetchApiOptions {
  method?: HttpMethod
  body?: unknown
  formData?: FormData
  auth?: boolean
  signal?: AbortSignal
}

let refreshInFlight: Promise<string | null> | null = null

function buildRequestInit(options: FetchApiOptions): RequestInit {
  const headers: Record<string, string> = { Accept: 'application/json' }
  let body: BodyInit | undefined
  if (options.formData) {
    body = options.formData
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }
  const token = getAccessToken()
  if ((options.auth ?? true) && token) {
    headers.Authorization = `Bearer ${token}`
  }
  return {
    method: options.method ?? 'GET',
    headers,
    body,
    credentials: 'include',
    signal: options.signal,
  }
}

async function sendRequest(path: string, options: FetchApiOptions): Promise<Response> {
  try {
    return await fetch(`${API_BASE_URL}${path}`, buildRequestInit(options))
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw networkError(error)
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshHandler = getRefreshHandler()
  if (!refreshHandler) return null
  if (!refreshInFlight) {
    refreshInFlight = refreshHandler()
      .catch(() => null)
      .finally(() => {
        refreshInFlight = null
      })
  }
  const token = await refreshInFlight
  if (token) setAccessToken(token)
  return token
}

async function readBody(response: Response): Promise<unknown> {
  const rawText = await response.text()
  if (!rawText) return undefined
  try {
    return JSON.parse(rawText) as unknown
  } catch {
    return rawText
  }
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  const error = apiErrorFromBody(response.status, await readBody(response))
  if (error.status === 402 && error.code === 'plan_upgrade_required') {
    emitPlanUpgradeRequired(error.details as PlanUpgradeDetails)
  }
  return error
}

export async function fetchApi<T>(path: string, options: FetchApiOptions = {}): Promise<T> {
  const useAuth = options.auth ?? true
  let response = await sendRequest(path, options)

  if (useAuth && response.status === 401) {
    const firstError = await errorFromResponse(response)
    if (firstError.code !== 'not_authenticated') throw firstError

    const refreshedToken = await refreshAccessToken()
    if (!refreshedToken) {
      getUnauthorizedHandler()?.()
      throw firstError
    }
    response = await sendRequest(path, options)
    if (response.status === 401) {
      getUnauthorizedHandler()?.()
    }
  }

  if (!response.ok) throw await errorFromResponse(response)

  if (response.status === 204) return undefined as T
  const body = await readBody(response)
  if (typeof body === 'string') {
    throw new ApiError(response.status, 'unknown_error', 'Server returned a non-JSON response')
  }
  return body as T
}
