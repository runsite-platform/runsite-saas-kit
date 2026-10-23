import type { OrgRole } from '@/types/api'

export type OrgAction =
  | 'manage_members'
  | 'manage_billing'
  | 'manage_settings'
  | 'delete_organization'
  | 'delete_any_file'

const MANAGER_ROLES: readonly OrgRole[] = ['owner', 'admin']
const OWNER_ONLY_ROLES: readonly OrgRole[] = ['owner']

const ROLES_BY_ACTION: Record<OrgAction, readonly OrgRole[]> = {
  manage_members: MANAGER_ROLES,
  manage_billing: MANAGER_ROLES,
  manage_settings: MANAGER_ROLES,
  delete_organization: OWNER_ONLY_ROLES,
  delete_any_file: MANAGER_ROLES,
}

export function canPerform(role: OrgRole, action: OrgAction): boolean {
  return ROLES_BY_ACTION[action].includes(role)
}
