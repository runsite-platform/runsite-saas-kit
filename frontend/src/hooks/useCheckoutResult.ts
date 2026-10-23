import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { billingService } from '@/services/billing'
import type { BillingOverview } from '@/types/api'
import { pollUntil } from '@/utils/pollUntil'

export const CHECKOUT_POLL_ATTEMPTS = 10
export const CHECKOUT_POLL_INTERVAL_MS = 2000
const CHECKOUT_PARAM = 'checkout'

export type CheckoutResult = 'idle' | 'polling' | 'succeeded' | 'processing' | 'canceled'

export function hasPaidAccess(overview: BillingOverview): boolean {
  const status = overview.subscription?.status
  return status === 'trialing' || status === 'active'
}

function resultForCheckoutParam(checkoutParam: string | null): CheckoutResult | null {
  if (checkoutParam === 'success') return 'polling'
  if (checkoutParam === 'canceled') return 'canceled'
  return null
}

export function useCheckoutResult(
  organizationId: string,
  onSettled: (overview: BillingOverview | null) => void,
): CheckoutResult {
  const [searchParams, setSearchParams] = useSearchParams()
  const checkoutParam = searchParams.get(CHECKOUT_PARAM)
  const [trackedCheckoutParam, setTrackedCheckoutParam] = useState(checkoutParam)
  const [result, setResult] = useState<CheckoutResult>(() => resultForCheckoutParam(checkoutParam) ?? 'idle')
  const onSettledRef = useRef(onSettled)

  if (checkoutParam !== trackedCheckoutParam) {
    setTrackedCheckoutParam(checkoutParam)
    const nextResult = resultForCheckoutParam(checkoutParam)
    if (nextResult) setResult(nextResult)
  }

  useEffect(() => {
    onSettledRef.current = onSettled
  })

  useEffect(() => {
    if (checkoutParam !== 'success' && checkoutParam !== 'canceled') return

    const clearCheckoutParam = () =>
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current)
          next.delete(CHECKOUT_PARAM)
          return next
        },
        { replace: true },
      )

    if (checkoutParam === 'canceled') {
      clearCheckoutParam()
      return
    }

    const controller = new AbortController()
    pollUntil(() => billingService.getBilling(organizationId, controller.signal), hasPaidAccess, {
      attempts: CHECKOUT_POLL_ATTEMPTS,
      intervalMs: CHECKOUT_POLL_INTERVAL_MS,
      signal: controller.signal,
    })
      .then((pollResult) => {
        if (controller.signal.aborted) return
        setResult(pollResult.done ? 'succeeded' : 'processing')
        onSettledRef.current(pollResult.value)
        clearCheckoutParam()
      })
      .catch(() => undefined)

    return () => controller.abort()
  }, [checkoutParam, organizationId, setSearchParams])

  return result
}
