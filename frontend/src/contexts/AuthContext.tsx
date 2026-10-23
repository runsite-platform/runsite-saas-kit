import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authService, type RegisterInput } from '@/services/auth'
import { meService } from '@/services/me'
import type { MeResponse, OrganizationSummary, User } from '@/types/api'
import { setAccessToken, setRefreshHandler, setUnauthorizedHandler } from '@/utils/tokenStore'

export type { RegisterInput }

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthContextValue {
  status: AuthStatus
  user: User | null
  organizations: OrganizationSummary[]
  impersonatedBy: string | null
  login(email: string, password: string): Promise<void>
  register(input: RegisterInput): Promise<void>
  logout(): Promise<void>
  acceptAccessToken(token: string): Promise<void>
  reloadMe(): Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<User | null>(null)
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([])
  const [impersonatedBy, setImpersonatedBy] = useState<string | null>(null)

  const applyMe = useCallback((me: MeResponse) => {
    setUser(me.user)
    setOrganizations(me.organizations)
    setImpersonatedBy(me.impersonated_by)
    setStatus('authenticated')
  }, [])

  const clearSession = useCallback(() => {
    setAccessToken(null)
    setUser(null)
    setOrganizations([])
    setImpersonatedBy(null)
    setStatus('anonymous')
  }, [])

  const reloadMe = useCallback(async () => {
    applyMe(await meService.getMe())
  }, [applyMe])

  const acceptAccessToken = useCallback(
    async (token: string) => {
      setAccessToken(token)
      await reloadMe()
    },
    [reloadMe],
  )

  useEffect(() => {
    setRefreshHandler(async () => {
      const token = await authService.refreshAccessToken()
      setAccessToken(token)
      return token
    })
    setUnauthorizedHandler(clearSession)
  }, [clearSession])

  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      const token = await authService.refreshAccessToken()
      if (cancelled) {
        return
      }
      if (!token) {
        clearSession()
        return
      }
      setAccessToken(token)
      try {
        const me = await meService.getMe()
        if (!cancelled) {
          applyMe(me)
        }
      } catch {
        if (!cancelled) {
          clearSession()
        }
      }
    }

    void restoreSession()
    return () => {
      cancelled = true
    }
  }, [applyMe, clearSession])

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await authService.login(email, password)
      await acceptAccessToken(response.access_token)
    },
    [acceptAccessToken],
  )

  const register = useCallback(
    async (input: RegisterInput) => {
      const response = await authService.register(input)
      await acceptAccessToken(response.access_token)
    },
    [acceptAccessToken],
  )

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } finally {
      clearSession()
    }
  }, [clearSession])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      organizations,
      impersonatedBy,
      login,
      register,
      logout,
      acceptAccessToken,
      reloadMe,
    }),
    [status, user, organizations, impersonatedBy, login, register, logout, acceptAccessToken, reloadMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}
