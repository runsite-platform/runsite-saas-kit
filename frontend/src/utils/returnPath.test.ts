import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearPendingInvitation,
  getLastOrganization,
  getSafeReturnPath,
  peekPendingInvitation,
  rememberLastOrganization,
  rememberPendingInvitation,
  withReturnPath,
} from '@/utils/returnPath'

describe('getSafeReturnPath', () => {
  it.each([
    ['/invite/abc', '/invite/abc'],
    ['/app/acme/members', '/app/acme/members'],
  ])('keeps the internal path %s', (rawPath, expected) => {
    expect(getSafeReturnPath(rawPath, '/app')).toBe(expected)
  })

  it.each([null, undefined, '', 'https://evil.example', '//evil.example', '/\\evil.example', 'app'])(
    'falls back for %s',
    (rawPath) => {
      expect(getSafeReturnPath(rawPath, '/app')).toBe('/app')
    },
  )
})

describe('withReturnPath', () => {
  it('encodes the return path', () => {
    expect(withReturnPath('/login', '/invite/a b')).toBe('/login?next=%2Finvite%2Fa%20b')
  })
})

describe('pending invitation memory', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  it('remembers and clears an invitation path', () => {
    rememberPendingInvitation('/invite/token-1')
    expect(peekPendingInvitation()).toBe('/invite/token-1')
    clearPendingInvitation()
    expect(peekPendingInvitation()).toBeNull()
  })

  it('ignores stored values that are not invitation paths', () => {
    window.sessionStorage.setItem('pending-invitation-path', 'https://evil.example')
    expect(peekPendingInvitation()).toBeNull()
  })
})

describe('last organization memory', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('returns the remembered slug', () => {
    expect(getLastOrganization()).toBeNull()
    rememberLastOrganization('acme')
    expect(getLastOrganization()).toBe('acme')
  })
})
