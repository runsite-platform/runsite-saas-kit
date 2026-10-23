import { useTranslation } from 'react-i18next'
import { Progress } from '@/components/ui/progress'
import type { BillingUsage, PlanLimits } from '@/types/api'
import { bytesToMegabytes, formatMegabytes } from '@/utils/billingFormat'

interface UsageBarsProps {
  usage: BillingUsage
  limits: PlanLimits
}

function percentOf(used: number, limit: number): number {
  if (limit <= 0) return 0
  return Math.min(100, Math.round((used / limit) * 100))
}

export function UsageBars({ usage, limits }: UsageBarsProps) {
  const { t, i18n } = useTranslation('billing')
  const storageMegabytes = bytesToMegabytes(usage.storage_bytes)
  const rows = [
    {
      key: 'members',
      label: t('usage.members'),
      percent: percentOf(usage.members, limits.members),
      value: `${usage.members} / ${limits.members}`,
    },
    {
      key: 'projects',
      label: t('usage.projects'),
      percent: percentOf(usage.projects, limits.projects),
      value: `${usage.projects} / ${limits.projects}`,
    },
    {
      key: 'storage',
      label: t('usage.storage'),
      percent: percentOf(storageMegabytes, limits.storage_mb),
      value: t('usage.storage_value', {
        used: formatMegabytes(storageMegabytes, i18n.language),
        limit: formatMegabytes(limits.storage_mb, i18n.language),
      }),
    },
  ]

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">{t('usage.title')}</h3>
      {rows.map((row) => (
        <div key={row.key} className="space-y-1.5">
          <div className="flex items-center justify-between gap-4 text-sm">
            <span>{row.label}</span>
            <span className="tabular-nums text-muted-foreground">{row.value}</span>
          </div>
          <Progress value={row.percent} aria-label={row.label} />
        </div>
      ))}
    </div>
  )
}
