import type { ChartRangeDays, OverviewCharts, OverviewStats } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export function getOverview(organizationId: string, signal?: AbortSignal): Promise<OverviewStats> {
  return fetchApi<OverviewStats>(`/orgs/${organizationId}/overview`, { signal })
}

export function getOverviewCharts(
  organizationId: string,
  days: ChartRangeDays,
  signal?: AbortSignal,
): Promise<OverviewCharts> {
  return fetchApi<OverviewCharts>(`/orgs/${organizationId}/overview/charts?days=${days}`, { signal })
}
