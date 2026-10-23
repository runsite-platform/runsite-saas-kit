import type { BillingInterval, BillingOverview, PaymentRecord, PlanInfo, RedirectUrl } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export const billingService = {
  listPlans(signal?: AbortSignal): Promise<PlanInfo[]> {
    return fetchApi<PlanInfo[]>('/plans', { auth: false, signal })
  },
  getBilling(organizationId: string, signal?: AbortSignal): Promise<BillingOverview> {
    return fetchApi<BillingOverview>(`/orgs/${organizationId}/billing`, { signal })
  },
  listPayments(organizationId: string): Promise<PaymentRecord[]> {
    return fetchApi<PaymentRecord[]>(`/orgs/${organizationId}/billing/payments`)
  },
  startCheckout(organizationId: string, planId: string, interval: BillingInterval): Promise<RedirectUrl> {
    return fetchApi<RedirectUrl>(`/orgs/${organizationId}/billing/checkout`, {
      method: 'POST',
      body: { plan_id: planId, interval },
    })
  },
  openPortal(organizationId: string): Promise<RedirectUrl> {
    return fetchApi<RedirectUrl>(`/orgs/${organizationId}/billing/portal`, { method: 'POST' })
  },
  cancelSubscription(organizationId: string): Promise<BillingOverview> {
    return fetchApi<BillingOverview>(`/orgs/${organizationId}/billing/cancel`, { method: 'POST' })
  },
}
