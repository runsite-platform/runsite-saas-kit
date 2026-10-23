import { CheckCircle2, Clock, Info, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BillingDisabledNotice } from '@/components/billing/BillingDisabledNotice'
import { CancelSubscriptionButton } from '@/components/billing/CancelSubscriptionButton'
import { PaymentHistoryTable } from '@/components/billing/PaymentHistoryTable'
import { PricingPlans } from '@/components/billing/PricingPlans'
import { UsageBars } from '@/components/billing/UsageBars'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { type CheckoutResult, useCheckoutResult } from '@/hooks/useCheckoutResult'
import { billingService } from '@/services/billing'
import type { BillingInterval, BillingOverview, PaymentRecord, SubscriptionSummary } from '@/types/api'

const BLOCKING_STATUSES = new Set(['trialing', 'active', 'past_due'])

type PendingAction = 'checkout' | 'portal' | 'cancel'

export default function BillingPage() {
  const { t } = useTranslation('billing')
  const { organization, can } = useCurrentOrganization()
  const { reloadMe } = useAuth()
  const canManageBilling = can('manage_billing')
  const [overview, setOverview] = useState<BillingOverview | null>(null)
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [loadError, setLoadError] = useState<unknown>(null)
  const [actionError, setActionError] = useState<unknown>(null)
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null)

  const loadPayments = useCallback(async () => {
    if (!canManageBilling) return
    setPayments(await billingService.listPayments(organization.id))
  }, [canManageBilling, organization.id])

  useEffect(() => {
    let isCurrentRequest = true
    billingService
      .getBilling(organization.id)
      .then(async (loadedOverview) => {
        const loadedPayments = canManageBilling ? await billingService.listPayments(organization.id) : []
        if (!isCurrentRequest) return
        setOverview(loadedOverview)
        setPayments(loadedPayments)
        setLoadError(null)
      })
      .catch((error: unknown) => {
        if (isCurrentRequest) setLoadError(error)
      })
    return () => {
      isCurrentRequest = false
    }
  }, [canManageBilling, organization.id])

  const checkoutResult = useCheckoutResult(organization.id, (latestOverview) => {
    if (latestOverview) setOverview(latestOverview)
    void reloadMe()
    void loadPayments().catch(() => undefined)
  })

  async function runAction(action: PendingAction, operation: () => Promise<void>) {
    setPendingAction(action)
    setActionError(null)
    try {
      await operation()
    } catch (error) {
      setActionError(error)
    } finally {
      setPendingAction(null)
    }
  }

  function startCheckout(planId: string, interval: BillingInterval) {
    void runAction('checkout', async () => {
      const { url } = await billingService.startCheckout(organization.id, planId, interval)
      window.location.assign(url)
    })
  }

  function openPortal() {
    void runAction('portal', async () => {
      const { url } = await billingService.openPortal(organization.id)
      window.location.assign(url)
    })
  }

  function cancelSubscription() {
    void runAction('cancel', async () => {
      setOverview(await billingService.cancelSubscription(organization.id))
    })
  }

  if (loadError) return <ApiErrorMessage error={loadError} />
  if (!overview) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-label={t('loading')} />
      </div>
    )
  }

  const subscription = overview.subscription
  const hasBlockingSubscription = subscription !== null && BLOCKING_STATUSES.has(subscription.status)
  const showUpgrade = overview.billing_enabled && canManageBilling && !hasBlockingSubscription
  const showProviderActions = overview.billing_enabled && canManageBilling && subscription !== null

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
        <p className="text-muted-foreground">{t('subtitle')}</p>
      </header>

      <CheckoutResultAlert result={checkoutResult} planName={overview.plan.name} />
      {actionError ? <ApiErrorMessage error={actionError} /> : null}

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{overview.plan.name}</CardTitle>
            {subscription ? (
              <Badge variant={subscription.status === 'past_due' ? 'destructive' : 'secondary'}>
                {t(`current.status.${subscription.status}`)}
              </Badge>
            ) : null}
          </div>
          <CardDescription>
            <SubscriptionDetails subscription={subscription} />
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {overview.plan_override ? (
            <Alert>
              <Info className="size-4" aria-hidden />
              <AlertTitle>
                {t('current.override', {
                  plan: t(`plan_names.${overview.plan_override.plan_id}`, {
                    defaultValue: overview.plan_override.plan_id,
                  }),
                })}
              </AlertTitle>
              {overview.plan_override.reason ? (
                <AlertDescription>{t('current.override_reason', { reason: overview.plan_override.reason })}</AlertDescription>
              ) : null}
            </Alert>
          ) : null}
          <UsageBars usage={overview.usage} limits={overview.plan.limits} />
          {showProviderActions ? (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" disabled={pendingAction !== null} onClick={openPortal}>
                {pendingAction === 'portal' ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
                {t('actions.manage')}
              </Button>
              {hasBlockingSubscription && !subscription.cancel_at_period_end ? (
                <CancelSubscriptionButton
                  periodEnd={subscription.current_period_end}
                  isBusy={pendingAction === 'cancel'}
                  disabled={pendingAction !== null}
                  onConfirm={cancelSubscription}
                />
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {!overview.billing_enabled ? <BillingDisabledNotice /> : null}

      {showUpgrade ? (
        <section className="space-y-4" aria-labelledby="billing-upgrade-heading">
          <div className="space-y-1">
            <h2 id="billing-upgrade-heading" className="text-lg font-semibold">
              {t('upgrade.title')}
            </h2>
            <p className="text-sm text-muted-foreground">{t('upgrade.subtitle')}</p>
          </div>
          {pendingAction === 'checkout' ? (
            <p role="status" className="text-sm text-muted-foreground">
              {t('actions.redirecting')}
            </p>
          ) : null}
          <div
            aria-busy={pendingAction === 'checkout'}
            className={pendingAction === 'checkout' ? 'pointer-events-none opacity-60' : undefined}
          >
            <PricingPlans mode="organization" onSelect={startCheckout} />
          </div>
        </section>
      ) : null}

      {canManageBilling && overview.billing_enabled ? (
        <section className="space-y-4" aria-labelledby="billing-payments-heading">
          <h2 id="billing-payments-heading" className="text-lg font-semibold">
            {t('payments.title')}
          </h2>
          <PaymentHistoryTable payments={payments} />
        </section>
      ) : null}
    </div>
  )
}

function SubscriptionDetails({ subscription }: { subscription: SubscriptionSummary | null }) {
  const { t, i18n } = useTranslation('billing')
  if (!subscription) return <>{t('current.free_hint')}</>

  const formatDate = (value: string) => new Date(value).toLocaleDateString(i18n.language, { dateStyle: 'medium' })
  if (subscription.status === 'past_due') return <>{t('current.past_due_hint')}</>
  if (subscription.status === 'trialing' && subscription.trial_ends_at) {
    return <>{t('current.trial_ends_on', { date: formatDate(subscription.trial_ends_at) })}</>
  }
  if (!subscription.current_period_end) return null
  const isEnding =
    subscription.cancel_at_period_end || subscription.status === 'canceled' || subscription.status === 'expired'
  return <>{t(isEnding ? 'current.ends_on' : 'current.renews_on', { date: formatDate(subscription.current_period_end) })}</>
}

function CheckoutResultAlert({ result, planName }: { result: CheckoutResult; planName: string }) {
  const { t } = useTranslation('billing')
  if (result === 'idle') return null
  if (result === 'polling') {
    return (
      <Alert role="status">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        <AlertTitle>{t('checkout.polling')}</AlertTitle>
      </Alert>
    )
  }
  if (result === 'succeeded') {
    return (
      <Alert role="status">
        <CheckCircle2 className="size-4" aria-hidden />
        <AlertTitle>{t('checkout.succeeded_title')}</AlertTitle>
        <AlertDescription>{t('checkout.succeeded', { plan: planName })}</AlertDescription>
      </Alert>
    )
  }
  if (result === 'processing') {
    return (
      <Alert role="status">
        <Clock className="size-4" aria-hidden />
        <AlertTitle>{t('checkout.processing_title')}</AlertTitle>
        <AlertDescription>{t('checkout.processing')}</AlertDescription>
      </Alert>
    )
  }
  return (
    <Alert role="status">
      <Info className="size-4" aria-hidden />
      <AlertDescription>{t('checkout.canceled')}</AlertDescription>
    </Alert>
  )
}
