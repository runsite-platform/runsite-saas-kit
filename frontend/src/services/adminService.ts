import { authService } from '@/services/auth'
import type {
  AdminOrganizationDetail,
  AdminOrganizationSummary,
  AdminUserDetail,
  AdminUserSummary,
  ChartRangeDays,
  ImpersonationResult,
  Page,
  PlanOverrideInput,
  PlatformMetrics,
  ResendVerificationResult,
  SetupChecklist,
} from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export interface AdminListParams {
  search?: string
  page: number
  pageSize: number
}

export interface AdminOrganizationListParams extends AdminListParams {
  planId?: string
}

function withQuery(path: string, params: Record<string, string | number | undefined>): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') searchParams.set(key, String(value))
  }
  const query = searchParams.toString()
  return query ? `${path}?${query}` : path
}

export function listUsers(params: AdminListParams, signal?: AbortSignal) {
  const path = withQuery('/admin/users', { search: params.search, page: params.page, size: params.pageSize })
  return fetchApi<Page<AdminUserSummary>>(path, { signal })
}

export function getUser(userId: string, signal?: AbortSignal) {
  return fetchApi<AdminUserDetail>(`/admin/users/${userId}`, { signal })
}

export function blockUser(userId: string) {
  return fetchApi<AdminUserSummary>(`/admin/users/${userId}/block`, { method: 'POST' })
}

export function unblockUser(userId: string) {
  return fetchApi<AdminUserSummary>(`/admin/users/${userId}/unblock`, { method: 'POST' })
}

export function resendVerification(userId: string) {
  return fetchApi<ResendVerificationResult>(`/admin/users/${userId}/resend-verification`, { method: 'POST' })
}

export function grantAdmin(userId: string) {
  return fetchApi<AdminUserSummary>(`/admin/users/${userId}/grant-admin`, { method: 'POST' })
}

export function revokeAdmin(userId: string) {
  return fetchApi<AdminUserSummary>(`/admin/users/${userId}/revoke-admin`, { method: 'POST' })
}

export function impersonateUser(userId: string) {
  return fetchApi<ImpersonationResult>(`/admin/users/${userId}/impersonate`, { method: 'POST' })
}

export function listOrganizations(params: AdminOrganizationListParams, signal?: AbortSignal) {
  const path = withQuery('/admin/organizations', {
    search: params.search,
    plan_id: params.planId,
    page: params.page,
    size: params.pageSize,
  })
  return fetchApi<Page<AdminOrganizationSummary>>(path, { signal })
}

export function getOrganization(organizationId: string, signal?: AbortSignal) {
  return fetchApi<AdminOrganizationDetail>(`/admin/organizations/${organizationId}`, { signal })
}

export function overridePlan(organizationId: string, input: PlanOverrideInput) {
  return fetchApi<AdminOrganizationDetail>(`/admin/organizations/${organizationId}/plan-override`, {
    method: 'POST',
    body: input,
  })
}

export function getPlatformMetrics(days: ChartRangeDays, signal?: AbortSignal) {
  return fetchApi<PlatformMetrics>(`/admin/metrics?days=${days}`, { signal })
}

export function getSetupChecklist(signal?: AbortSignal) {
  return fetchApi<SetupChecklist>('/admin/setup', { signal })
}

/** Resolves to the superadmin's own access token from the untouched refresh cookie, or null when it is gone. */
export function refreshAdminSession(): Promise<string | null> {
  return authService.refreshAccessToken()
}
