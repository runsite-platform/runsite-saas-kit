import { useState } from 'react'
import { Building2, CircleDollarSign, Clock, Repeat, TrendingDown, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { DailySeriesChart } from '@/components/shared/DailySeriesChart'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { RangeToggle } from '@/components/shared/RangeToggle'
import { StatCard } from '@/components/shared/StatCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useApiQuery } from '@/hooks/useApiQuery'
import { getPlatformMetrics } from '@/services/adminService'
import type { ChartRangeDays } from '@/types/api'
import { formatRate, formatUsdCents } from '@/utils/statsFormatting'

export function AdminDashboardPage() {
  const { t, i18n } = useTranslation('admin')
  const [rangeDays, setRangeDays] = useState<ChartRangeDays>(30)
  const metrics = useApiQuery((signal) => getPlatformMetrics(rangeDays, signal), [rangeDays])
  const data = metrics.data

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('dashboard.title')}</h1>
          <p className="text-sm text-muted-foreground">{t('dashboard.subtitle')}</p>
        </div>
        <RangeToggle value={rangeDays} onChange={setRangeDays} />
      </div>

      <QueryErrorMessage error={metrics.error} />
      {!data && metrics.isLoading ? <p className="text-sm text-muted-foreground">{t('common.loading')}</p> : null}

      {data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard
              title={t('dashboard.mrr')}
              value={formatUsdCents(data.mrr_cents, i18n.language)}
              hint={t('dashboard.mrr_hint')}
              icon={<CircleDollarSign className="size-4" aria-hidden="true" />}
            />
            <StatCard
              title={t('dashboard.active_subscriptions')}
              value={data.active_subscriptions}
              hint={t('dashboard.past_due_hint', { count: data.past_due_subscriptions })}
              icon={<Repeat className="size-4" aria-hidden="true" />}
            />
            <StatCard
              title={t('dashboard.trialing_subscriptions')}
              value={data.trialing_subscriptions}
              icon={<Clock className="size-4" aria-hidden="true" />}
            />
            <StatCard
              title={t('dashboard.conversion')}
              value={formatRate(data.trial_conversion.rate, i18n.language)}
              hint={t('dashboard.conversion_hint', {
                converted: data.trial_conversion.converted,
                ended: data.trial_conversion.ended_trials,
                days: data.trial_conversion.window_days,
              })}
            />
            <StatCard
              title={t('dashboard.churned')}
              value={data.churned_last_30_days}
              hint={t('dashboard.churned_hint')}
              icon={<TrendingDown className="size-4" aria-hidden="true" />}
            />
            <StatCard
              title={t('dashboard.total_users')}
              value={data.total_users}
              hint={`${t('dashboard.total_organizations')}: ${data.total_organizations}`}
              icon={<Users className="size-4" aria-hidden="true" />}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>{t('dashboard.signups')}</CardTitle>
              </CardHeader>
              <CardContent>
                <DailySeriesChart series={data.signups_per_day} seriesLabel={t('dashboard.signups_series')} kind="line" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="size-4" aria-hidden="true" />
                  {t('dashboard.new_organizations')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <DailySeriesChart
                  series={data.new_organizations_per_day}
                  seriesLabel={t('dashboard.new_organizations_series')}
                />
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
