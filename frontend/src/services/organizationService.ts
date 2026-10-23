import type { LogoResponse, OrganizationDetail, OrganizationSummary } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export interface OrganizationUpdateInput {
  name?: string
  slug?: string
}

export function listOrganizations(signal?: AbortSignal): Promise<OrganizationSummary[]> {
  return fetchApi<OrganizationSummary[]>('/orgs', { signal })
}

export function createOrganization(name: string): Promise<OrganizationSummary> {
  return fetchApi<OrganizationSummary>('/orgs', { method: 'POST', body: { name } })
}

export function getOrganization(organizationId: string, signal?: AbortSignal): Promise<OrganizationDetail> {
  return fetchApi<OrganizationDetail>(`/orgs/${organizationId}`, { signal })
}

export function updateOrganization(
  organizationId: string,
  input: OrganizationUpdateInput,
): Promise<OrganizationDetail> {
  return fetchApi<OrganizationDetail>(`/orgs/${organizationId}`, { method: 'PATCH', body: input })
}

export function deleteOrganization(organizationId: string): Promise<void> {
  return fetchApi<void>(`/orgs/${organizationId}`, { method: 'DELETE' })
}

export function transferOwnership(organizationId: string, membershipId: string): Promise<void> {
  return fetchApi<void>(`/orgs/${organizationId}/transfer-ownership`, {
    method: 'POST',
    body: { membership_id: membershipId },
  })
}

export async function uploadLogo(organizationId: string, file: File): Promise<LogoResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return fetchApi<LogoResponse>(`/orgs/${organizationId}/logo`, { method: 'PUT', formData })
}

export async function removeLogo(organizationId: string): Promise<void> {
  await fetchApi<void>(`/orgs/${organizationId}/logo`, { method: 'DELETE' })
}
