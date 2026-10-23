import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { useApiQuery } from '@/hooks/useApiQuery'
import { billingService } from '@/services/billing'
import type { BillingOverview } from '@/types/api'
import { isPaidPlan } from '@/utils/billingFormat'

const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000

interface PlanCardContent {
  title: string
  detail: string | null
  progressPercent: number | null
  isWarning: boolean
}

function percentOf(used: number, limit: number): number {
  if (limit <= 0) return 0
  return Math.min(100, Math.max(0, (used / limit) * 100))
}

export function SidebarPlanCard({ onNavigate }: { onNavigate?: () => void }) {
  const { t, i18n } = useTranslation('billing')
  const { organization, can } = useCurrentOrganization()
  const { data: loadedBilling } = useApiQuery(
    async (signal) => {
      const billingOverview = await billingService.getBilling(organization.id, signal)
      return { overview: billingOverview, loadedAtMs: Date.now() }
    },
    [organization.id, organization.plan_id],
  )
  if (!loadedBilling) return null
  const { overview, loadedAtMs } = loadedBilling

  const formatDate = (isoDate: string) =>
    new Intl.DateTimeFormat(i18n.language, { month: 'short', day: 'numeric' }).format(new Date(isoDate))

  function describePlan(billingOverview: BillingOverview): PlanCardContent {
    const { plan, subscription, usage } = billingOverview
    const planName = t(`plan_names.${plan.id}`, { defaultValue: plan.name })

    if (subscription?.status === 'trialing' && subscription.trial_ends_at) {
      const daysLeft = Math.max(
        0,
        Math.ceil((new Date(subscription.trial_ends_at).getTime() - loadedAtMs) / MILLISECONDS_PER_DAY),
      )
      const trialLength = Math.max(plan.trial_days, daysLeft)
      return {
        title: t('sidebar.trial', { plan: planName }),
        detail: t('sidebar.days_left', { count: daysLeft }),
        progressPercent: percentOf(trialLength - daysLeft, trialLength),
        isWarning: daysLeft <= 3,
      }
    }
    if (subscription?.status === 'past_due') {
      return { title: t('sidebar.plan', { plan: planName }), detail: t('sidebar.past_due'), progressPercent: null, isWarning: true }
    }
    if (isPaidPlan(plan) && subscription?.current_period_end) {
      const dateKey = subscription.cancel_at_period_end ? 'sidebar.ends' : 'sidebar.renews'
      return {
        title: t('sidebar.plan', { plan: planName }),
        detail: t(dateKey, { date: formatDate(subscription.current_period_end) }),
        progressPercent: null,
        isWarning: subscription.cancel_at_period_end,
      }
    }
    return {
      title: t('sidebar.plan', { plan: planName }),
      detail: t('sidebar.projects_used', { used: usage.projects, limit: plan.limits.projects }),
      progressPercent: percentOf(usage.projects, plan.limits.projects),
      isWarning: usage.projects >= plan.limits.projects,
    }
  }

  const planCard = describePlan(overview)
  const isOnPaidPlan = isPaidPlan(overview.plan) && overview.subscription?.status !== 'trialing'
  const canOpenBilling = can('manage_billing')

  return (
    <div className="space-y-2.5 rounded-lg border bg-background p-3 shadow-xs">
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate text-sm font-semibold">{planCard.title}</span>
        {planCard.detail ? (
          <span
            className={
              planCard.isWarning ? 'shrink-0 text-xs font-medium text-destructive' : 'shrink-0 text-xs text-muted-foreground'
            }
          >
            {planCard.detail}
          </span>
        ) : null}
      </div>
      {planCard.progressPercent !== null ? (
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className={planCard.isWarning ? 'h-full rounded-full bg-destructive' : 'h-full rounded-full bg-primary'}
            style={{ width: `${planCard.progressPercent}%` }} />
        </div>
      ) : null}
      {canOpenBilling ? (
        <Button asChild size="sm" variant={isOnPaidPlan ? 'outline' : 'default'} className="w-full">
          <Link to={`/app/${organization.slug}/billing`} onClick={onNavigate}>
            {isOnPaidPlan ? t('sidebar.manage') : t('sidebar.upgrade')}
          </Link>
        </Button>
      ) : null}
    </div>
  )
}
