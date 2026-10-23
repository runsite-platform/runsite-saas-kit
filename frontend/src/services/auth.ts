import type { StatusResponse, TokenResponse } from '@/types/api'
import { ApiError } from '@/utils/apiError'
import { fetchApi } from '@/utils/fetchApi'

export interface RegisterInput {
  email: string
  password: string
  full_name: string
}

export const GOOGLE_START_URL = '/api/auth/google/start'

let refreshInFlight: Promise<string | null> | null = null

async function requestNewAccessToken(): Promise<string | null> {
  try {
    const response = await fetchApi<TokenResponse>('/auth/refresh', { method: 'POST', auth: false })
    return response.access_token
  } catch (error) {
    if (error instanceof ApiError) {
      return null
    }
    throw error
  }
}

export const authService = {
  register(input: RegisterInput): Promise<TokenResponse> {
    return fetchApi<TokenResponse>('/auth/register', { method: 'POST', body: input, auth: false })
  },

  login(email: string, password: string): Promise<TokenResponse> {
    return fetchApi<TokenResponse>('/auth/login', { method: 'POST', body: { email, password }, auth: false })
  },

  logout(): Promise<StatusResponse> {
    return fetchApi<StatusResponse>('/auth/logout', { method: 'POST', auth: false })
  },

  /** One refresh at a time: the refresh token rotates, so a parallel second call would look like reuse. */
  refreshAccessToken(): Promise<string | null> {
    if (!refreshInFlight) {
      refreshInFlight = requestNewAccessToken().finally(() => {
        refreshInFlight = null
      })
    }
    return refreshInFlight
  },

  verifyEmail(token: string): Promise<StatusResponse> {
    return fetchApi<StatusResponse>('/auth/verify-email', { method: 'POST', body: { token }, auth: false })
  },

  resendVerification(email: string): Promise<StatusResponse> {
    return fetchApi<StatusResponse>('/auth/resend-verification', { method: 'POST', body: { email }, auth: false })
  },

  forgotPassword(email: string): Promise<StatusResponse> {
    return fetchApi<StatusResponse>('/auth/forgot-password', { method: 'POST', body: { email }, auth: false })
  },

  resetPassword(token: string, password: string): Promise<StatusResponse> {
    return fetchApi<StatusResponse>('/auth/reset-password', {
      method: 'POST',
      body: { token, password },
      auth: false,
    })
  },
}
