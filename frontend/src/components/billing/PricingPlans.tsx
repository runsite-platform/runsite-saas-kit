import { Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { IntervalToggle } from '@/components/billing/IntervalToggle'
import { PlanCard } from '@/components/billing/PlanCard'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { useAuth } from '@/contexts/AuthContext'
import { billingService } from '@/services/billing'
import type { BillingInterval, PlanInfo } from '@/types/api'
import { isPaidPlan } from '@/utils/billingFormat'

export type PricingPlansMode = 'public' | 'organization'

interface PricingPlansProps {
  mode?: PricingPlansMode
  onSelect?: (planId: string, interval: BillingInterval) => void
}

export function PricingPlans({ mode = 'public', onSelect }: PricingPlansProps) {
  const { t } = useTranslation('billing')
  const navigate = useNavigate()
  const { orgSlug } = useParams()
  const { status, organizations } = useAuth()
  const [plans, setPlans] = useState<PlanInfo[] | null>(null)
  const [loadError, setLoadError] = useState<unknown>(null)
  const [billingInterval, setBillingInterval] = useState<BillingInterval>('monthly')
  const currentPlanId =
    mode === 'organization' ? organizations.find((organization) => organization.slug === orgSlug)?.plan_id : undefined

  useEffect(() => {
    const controller = new AbortController()
    billingService
      .listPlans(controller.signal)
      .then(setPlans)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLoadError(error)
      })
    return () => controller.abort()
  }, [])

  function selectPlan(plan: PlanInfo) {
    if (onSelect) {
      onSelect(plan.id, billingInterval)
      return
    }
    const firstOrganization = organizations[0]
    if (status === 'authenticated' && firstOrganization) {
      navigate(`/app/${firstOrganization.slug}/billing`)
    } else {
      navigate('/register')
    }
  }

  function actionLabelFor(plan: PlanInfo): string {
    if (!isPaidPlan(plan)) return t('plan.get_started')
    return plan.trial_days > 0 ? t('plan.start_trial') : t('plan.choose')
  }

  if (loadError) return <ApiErrorMessage error={loadError} />
  if (!plans) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-label={t('loading')} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-center">
        <IntervalToggle value={billingInterval} onChange={setBillingInterval} />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        {plans.map((plan) => {
          const isCurrent = plan.id === currentPlanId
          const isSelectable = mode === 'public' || isPaidPlan(plan)
          return (
            <PlanCard
              key={plan.id}
              plan={plan}
              interval={billingInterval}
              isCurrent={isCurrent}
              actionLabel={actionLabelFor(plan)}
              onSelect={isSelectable ? selectPlan : undefined}
            />
          )
        })}
      </div>
    </div>
  )
}
