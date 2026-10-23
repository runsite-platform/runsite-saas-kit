import { FolderKanban, HardDrive, Sparkles, Users } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { UpgradeChartsCard } from '@/components/overview/UpgradeChartsCard'
import { DailySeriesChart } from '@/components/shared/DailySeriesChart'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { RangeToggle } from '@/components/shared/RangeToggle'
import { StatCard } from '@/components/shared/StatCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { useApiQuery } from '@/hooks/useApiQuery'
import { getOverview, getOverviewCharts } from '@/services/overviewService'
import type { ChartRangeDays, OverviewCharts } from '@/types/api'
import { formatStorageBytes, totalCount, usagePercent } from '@/utils/statsFormatting'

export default function OverviewPage() {
  const { t } = useTranslation('overview')
  const { organization } = useCurrentOrganization()
  const [rangeDays, setRangeDays] = useState<ChartRangeDays>(30)
  const stats = useApiQuery((signal) => getOverview(organization.id, signal), [organization.id])
  const hasAnalytics = stats.data?.has_analytics ?? false
  const charts = useApiQuery<OverviewCharts | null>(
    (signal) => (hasAnalytics ? getOverviewCharts(organization.id, rangeDays, signal) : Promise.resolve(null)),
    [organization.id, rangeDays, hasAnalytics],
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
        <p className="text-sm text-muted-foreground">{t('subtitle', { organization: organization.name })}</p>
      </div>

      <QueryErrorMessage error={stats.error} />

      {stats.data ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title={t('stats.projects')}
            value={stats.data.projects_count}
            hint={t('stats.of_limit', { limit: stats.data.projects_limit })}
            usagePercent={usagePercent(stats.data.projects_count, stats.data.projects_limit)}
            icon={<FolderKanban className="size-4" aria-hidden="true" />}
          />
          <StatCard
            title={t('stats.members')}
            value={stats.data.members_count}
            hint={t('stats.of_limit', { limit: stats.data.members_limit })}
            usagePercent={usagePercent(stats.data.members_count, stats.data.members_limit)}
            icon={<Users className="size-4" aria-hidden="true" />}
          />
          <StatCard
            title={t('stats.storage')}
            value={formatStorageBytes(stats.data.storage_used_bytes)}
            hint={t('stats.storage_of_limit', {
              used: formatStorageBytes(stats.data.storage_used_bytes),
              limit: formatStorageBytes(stats.data.storage_limit_bytes),
            })}
            usagePercent={usagePercent(stats.data.storage_used_bytes, stats.data.storage_limit_bytes)}
            icon={<HardDrive className="size-4" aria-hidden="true" />}
          />
          <StatCard
            title={t('stats.plan')}
            value={t(`plans.${stats.data.plan_id}`, { defaultValue: stats.data.plan_id })}
            hint={
              <Link className="underline underline-offset-4" to={`/app/${organization.slug}/billing`}>
                {t('stats.manage_billing')}
              </Link>
            }
            icon={<Sparkles className="size-4" aria-hidden="true" />}
          />
        </div>
      ) : stats.isLoading ? (
        <p className="text-sm text-muted-foreground">{t('loading')}</p>
      ) : null}

      {stats.data && !hasAnalytics ? <UpgradeChartsCard organizationSlug={organization.slug} /> : null}

      {hasAnalytics ? (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle>{t('charts.projects_per_day')}</CardTitle>
              {charts.data ? (
                <p className="text-sm text-muted-foreground">
                  {t('charts.total', { count: totalCount(charts.data.projects_per_day) })}
                </p>
              ) : null}
            </div>
            <RangeToggle value={rangeDays} onChange={setRangeDays} />
          </CardHeader>
          <CardContent>
            <QueryErrorMessage error={charts.error} />
            {charts.data ? (
              <DailySeriesChart series={charts.data.projects_per_day} seriesLabel={t('charts.projects_series')} />
            ) : charts.isLoading ? (
              <p className="py-24 text-center text-sm text-muted-foreground">{t('loading')}</p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
