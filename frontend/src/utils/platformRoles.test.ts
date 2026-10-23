import { describe, expect, it } from 'vitest'
import type { User } from '@/types/api'
import { hasPlatformRole, isPlatformStaff, isSuperadmin, SUPERADMIN_ROLES } from './platformRoles'

const withRole = (role: string) => ({ platform_role: role }) as Pick<User, 'platform_role'>

describe('platform roles', () => {
  it('lets admins and superadmins into the admin area', () => {
    expect(isPlatformStaff(withRole('admin'), null)).toBe(true)
    expect(isPlatformStaff(withRole('superadmin'), null)).toBe(true)
    expect(isPlatformStaff(withRole('user'), null)).toBe(false)
    expect(isPlatformStaff(null, null)).toBe(false)
  })

  it('keeps superadmin-only areas for superadmins', () => {
    expect(isSuperadmin(withRole('superadmin'), null)).toBe(true)
    expect(isSuperadmin(withRole('admin'), null)).toBe(false)
    expect(hasPlatformRole(withRole('admin'), null, SUPERADMIN_ROLES)).toBe(false)
  })

  it('denies everything while impersonating', () => {
    expect(isPlatformStaff(withRole('superadmin'), 'impersonator-id')).toBe(false)
    expect(isSuperadmin(withRole('superadmin'), 'impersonator-id')).toBe(false)
  })
})
