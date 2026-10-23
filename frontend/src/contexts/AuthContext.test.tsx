import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import type { MeResponse } from '@/types/api'
import { getAccessToken, setAccessToken } from '@/utils/tokenStore'

const mocks = vi.hoisted(() => ({
  refreshAccessToken: vi.fn<() => Promise<string | null>>(),
  getMe: vi.fn<() => Promise<MeResponse>>(),
}))

vi.mock('@/services/auth', () => ({
  authService: {
    refreshAccessToken: mocks.refreshAccessToken,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}))

vi.mock('@/services/me', () => ({
  meService: { getMe: mocks.getMe },
}))

const sampleMe: MeResponse = {
  user: {
    id: '7b0e6d2a-1111-4c3f-9d55-2a4b5c6d7e8f',
    email: 'ann@example.com',
    full_name: 'Ann',
    avatar_url: null,
    platform_role: 'user',
    is_email_verified: true,
    has_password: true,
    google_linked: false,
    created_at: '2026-10-23T10:00:00Z',
  },
  organizations: [],
  impersonated_by: null,
}

function SessionProbe() {
  const { status, user } = useAuth()
  return <p>{`${status}:${user?.email ?? 'nobody'}`}</p>
}

function renderWithProvider() {
  return render(
    <AuthProvider>
      <SessionProbe />
    </AuthProvider>,
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    mocks.refreshAccessToken.mockReset()
    mocks.getMe.mockReset()
    setAccessToken(null)
  })

  afterEach(() => {
    cleanup()
  })

  it('restores the session through the refresh cookie', async () => {
    mocks.refreshAccessToken.mockResolvedValue('access-token-1')
    mocks.getMe.mockResolvedValue(sampleMe)

    renderWithProvider()

    expect(screen.getByText('loading:nobody')).toBeTruthy()
    expect(await screen.findByText('authenticated:ann@example.com')).toBeTruthy()
    expect(getAccessToken()).toBe('access-token-1')
    expect(mocks.refreshAccessToken).toHaveBeenCalledTimes(1)
  })

  it('becomes anonymous when the refresh fails', async () => {
    mocks.refreshAccessToken.mockResolvedValue(null)

    renderWithProvider()

    expect(await screen.findByText('anonymous:nobody')).toBeTruthy()
    expect(mocks.getMe).not.toHaveBeenCalled()
    expect(getAccessToken()).toBeNull()
  })

  it('becomes anonymous when loading the profile fails', async () => {
    mocks.refreshAccessToken.mockResolvedValue('access-token-1')
    mocks.getMe.mockRejectedValue(new Error('boom'))

    renderWithProvider()

    expect(await screen.findByText('anonymous:nobody')).toBeTruthy()
    expect(getAccessToken()).toBeNull()
  })
})
