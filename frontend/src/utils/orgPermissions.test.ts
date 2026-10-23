import { describe, expect, it } from 'vitest'
import type { OrgRole } from '@/types/api'
import { canPerform, type OrgAction } from '@/utils/orgPermissions'

const EXPECTED_PERMISSIONS: Record<OrgAction, Record<OrgRole, boolean>> = {
  manage_members: { owner: true, admin: true, member: false },
  manage_billing: { owner: true, admin: true, member: false },
  manage_settings: { owner: true, admin: true, member: false },
  delete_organization: { owner: true, admin: false, member: false },
  delete_any_file: { owner: true, admin: true, member: false },
}

describe('canPerform', () => {
  for (const [action, expectedByRole] of Object.entries(EXPECTED_PERMISSIONS) as [
    OrgAction,
    Record<OrgRole, boolean>,
  ][]) {
    for (const [role, isAllowed] of Object.entries(expectedByRole) as [OrgRole, boolean][]) {
      it(`${role} ${isAllowed ? 'can' : 'cannot'} ${action}`, () => {
        expect(canPerform(role, action)).toBe(isAllowed)
      })
    }
  }
})
