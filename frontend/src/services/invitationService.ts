import type {
  InvitableRole,
  Invitation,
  InvitationCreated,
  InvitationPreview,
  OrganizationSummary,
} from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export interface InvitationCreateInput {
  email: string
  role: InvitableRole
}

export function listInvitations(organizationId: string, signal?: AbortSignal): Promise<Invitation[]> {
  return fetchApi<Invitation[]>(`/orgs/${organizationId}/invitations`, { signal })
}

export function createInvitation(organizationId: string, input: InvitationCreateInput): Promise<InvitationCreated> {
  return fetchApi<InvitationCreated>(`/orgs/${organizationId}/invitations`, { method: 'POST', body: input })
}

export function revokeInvitation(organizationId: string, invitationId: string): Promise<void> {
  return fetchApi<void>(`/orgs/${organizationId}/invitations/${invitationId}`, { method: 'DELETE' })
}

export function getInvitationPreview(token: string, signal?: AbortSignal): Promise<InvitationPreview> {
  return fetchApi<InvitationPreview>(`/invitations/${encodeURIComponent(token)}`, { auth: false, signal })
}

export function acceptInvitation(token: string): Promise<OrganizationSummary> {
  return fetchApi<OrganizationSummary>(`/invitations/${encodeURIComponent(token)}/accept`, { method: 'POST' })
}
