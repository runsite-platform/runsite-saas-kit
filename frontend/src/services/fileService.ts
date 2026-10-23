import type { DownloadUrlResponse, Page, StoredFile } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export const MAX_FILE_BYTES = 25 * 1024 * 1024

const MAX_PAGE_SIZE = 100

export async function listFiles(organizationId: string): Promise<StoredFile[]> {
  const page = await fetchApi<Page<StoredFile>>(`/orgs/${organizationId}/files?size=${MAX_PAGE_SIZE}`)
  return page.items
}

export async function uploadFile(organizationId: string, file: File): Promise<StoredFile> {
  const formData = new FormData()
  formData.append('file', file)
  return fetchApi<StoredFile>(`/orgs/${organizationId}/files`, { method: 'POST', formData })
}

export async function getDownloadUrl(organizationId: string, fileId: string): Promise<DownloadUrlResponse> {
  return fetchApi<DownloadUrlResponse>(`/orgs/${organizationId}/files/${fileId}/download`)
}

export async function deleteFile(organizationId: string, fileId: string): Promise<void> {
  await fetchApi<void>(`/orgs/${organizationId}/files/${fileId}`, { method: 'DELETE' })
}
