import type { User } from '@/types/api'

type RoleHolder = Pick<User, 'platform_role'> | null

export const PLATFORM_STAFF_ROLES: readonly string[] = ['admin', 'superadmin']
export const SUPERADMIN_ROLES: readonly string[] = ['superadmin']

export function hasPlatformRole(
  user: RoleHolder,
  impersonatedBy: string | null,
  allowedRoles: readonly string[],
): boolean {
  if (!user || impersonatedBy) return false
  return allowedRoles.includes(user.platform_role)
}

export function isPlatformStaff(user: RoleHolder, impersonatedBy: string | null): boolean {
  return hasPlatformRole(user, impersonatedBy, PLATFORM_STAFF_ROLES)
}

export function isSuperadmin(user: RoleHolder, impersonatedBy: string | null): boolean {
  return hasPlatformRole(user, impersonatedBy, SUPERADMIN_ROLES)
}
