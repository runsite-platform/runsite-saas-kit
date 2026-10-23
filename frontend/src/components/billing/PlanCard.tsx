import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { BillingInterval, PlanInfo } from '@/types/api'
import { formatCents, formatMegabytes, isPaidPlan } from '@/utils/billingFormat'

interface PlanCardProps {
  plan: PlanInfo
  interval: BillingInterval
  isCurrent?: boolean
  actionLabel?: string
  onSelect?: (plan: PlanInfo) => void
}

export function PlanCard({ plan, interval, isCurrent = false, actionLabel, onSelect }: PlanCardProps) {
  const { t, i18n } = useTranslation('billing')
  const priceCents = interval === 'monthly' ? plan.price_monthly_cents : plan.price_yearly_cents
  const isAvailable = plan.available[interval]
  const benefits = [
    t('limits.members', { count: plan.limits.members }),
    t('limits.projects', { count: plan.limits.projects }),
    t('limits.storage', { size: formatMegabytes(plan.limits.storage_mb, i18n.language) }),
    ...plan.features.map((feature) => t(`features.${feature}`, { defaultValue: feature })),
  ]
  const buttonLabel = !isAvailable ? t('plan.unavailable') : isCurrent ? t('plan.current') : (actionLabel ?? t('plan.choose'))

  return (
    <Card className={cn('flex h-full flex-col', isCurrent && 'border-primary')}>
      <CardHeader className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle>{plan.name}</CardTitle>
          {isCurrent ? <Badge>{t('plan.current')}</Badge> : null}
        </div>
        <CardDescription>
          <span className="text-3xl font-semibold tabular-nums text-foreground">
            {isPaidPlan(plan) ? formatCents(priceCents, 'USD', i18n.language) : t('plan.free_price')}
          </span>
          {isPaidPlan(plan) ? <span className="ml-1">{t(`plan.per_${interval}`)}</span> : null}
        </CardDescription>
        {plan.trial_days > 0 ? (
          <p className="text-sm text-muted-foreground">{t('plan.trial', { count: plan.trial_days })}</p>
        ) : null}
      </CardHeader>
      <CardContent className="flex-1">
        <ul className="space-y-2 text-sm">
          {benefits.map((benefit) => (
            <li key={benefit} className="flex items-start gap-2">
              <Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              <span>{benefit}</span>
            </li>
          ))}
        </ul>
      </CardContent>
      {onSelect ? (
        <CardFooter>
          <Button className="w-full" disabled={isCurrent || !isAvailable} onClick={() => onSelect(plan)}>
            {buttonLabel}
          </Button>
        </CardFooter>
      ) : null}
    </Card>
  )
}
