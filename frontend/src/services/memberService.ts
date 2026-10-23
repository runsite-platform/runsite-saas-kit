import type { InvitableRole, Member } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export function listMembers(organizationId: string, signal?: AbortSignal): Promise<Member[]> {
  return fetchApi<Member[]>(`/orgs/${organizationId}/members`, { signal })
}

export function changeMemberRole(organizationId: string, membershipId: string, role: InvitableRole): Promise<Member> {
  return fetchApi<Member>(`/orgs/${organizationId}/members/${membershipId}`, { method: 'PATCH', body: { role } })
}

export function removeMember(organizationId: string, membershipId: string): Promise<void> {
  return fetchApi<void>(`/orgs/${organizationId}/members/${membershipId}`, { method: 'DELETE' })
}
