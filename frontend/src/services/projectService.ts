import type { Page, Project, ProjectInput, ProjectStatus, ProjectUpdateInput } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

const MAX_PAGE_SIZE = 100

export async function listProjects(organizationId: string, status?: ProjectStatus): Promise<Project[]> {
  const query = new URLSearchParams({ size: String(MAX_PAGE_SIZE) })
  if (status) query.set('status', status)
  const page = await fetchApi<Page<Project>>(`/orgs/${organizationId}/projects?${query}`)
  return page.items
}

export async function getProject(organizationId: string, projectId: string): Promise<Project> {
  return fetchApi<Project>(`/orgs/${organizationId}/projects/${projectId}`)
}

export async function createProject(organizationId: string, input: ProjectInput): Promise<Project> {
  return fetchApi<Project>(`/orgs/${organizationId}/projects`, { method: 'POST', body: input })
}

export async function updateProject(
  organizationId: string,
  projectId: string,
  input: ProjectUpdateInput,
): Promise<Project> {
  return fetchApi<Project>(`/orgs/${organizationId}/projects/${projectId}`, { method: 'PATCH', body: input })
}

export async function deleteProject(organizationId: string, projectId: string): Promise<void> {
  await fetchApi<void>(`/orgs/${organizationId}/projects/${projectId}`, { method: 'DELETE' })
}
