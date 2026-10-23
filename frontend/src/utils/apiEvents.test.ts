// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'
import { emitPlanUpgradeRequired, onPlanUpgradeRequired } from '@/utils/apiEvents'

describe('apiEvents', () => {
  it('delivers details to subscribers until they unsubscribe', () => {
    const listener = vi.fn()
    const unsubscribe = onPlanUpgradeRequired(listener)

    emitPlanUpgradeRequired({ feature: 'analytics', required_plan: 'pro' })
    unsubscribe()
    emitPlanUpgradeRequired({ feature: 'analytics', required_plan: 'pro' })

    expect(listener).toHaveBeenCalledTimes(1)
    expect(listener).toHaveBeenCalledWith({ feature: 'analytics', required_plan: 'pro' })
  })
})
