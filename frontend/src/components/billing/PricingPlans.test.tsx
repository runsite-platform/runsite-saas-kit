import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import '@/i18n'
import { PricingPlans } from '@/components/billing/PricingPlans'
import type { PlanInfo } from '@/types/api'

const { testPlans } = vi.hoisted(() => {
  const testPlans: PlanInfo[] = [
    {
      id: 'free',
      name: 'Free',
      price_monthly_cents: 0,
      price_yearly_cents: 0,
      trial_days: 0,
      limits: { members: 3, projects: 3, storage_mb: 100 },
      features: ['file_uploads'],
      available: { monthly: true, yearly: true },
    },
    {
      id: 'pro',
      name: 'Pro',
      price_monthly_cents: 1900,
      price_yearly_cents: 19000,
      trial_days: 14,
      limits: { members: 10, projects: 100, storage_mb: 5000 },
      features: ['analytics', 'file_uploads'],
      available: { monthly: true, yearly: false },
    },
  ]
  return { testPlans }
})

vi.mock('@/services/billing', () => ({
  billingService: { listPlans: vi.fn(async () => testPlans) },
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ status: 'anonymous', organizations: [] }),
}))

function renderPlans(props: Parameters<typeof PricingPlans>[0] = {}) {
  return render(
    <MemoryRouter>
      <PricingPlans {...props} />
    </MemoryRouter>,
  )
}

describe('PricingPlans', () => {
  afterEach(() => cleanup())

  it('renders every plan with monthly prices by default', async () => {
    renderPlans()

    expect(await screen.findByText('Pro')).not.toBeNull()
    expect(screen.getByText('$19')).not.toBeNull()
    expect(screen.getByText('14-day free trial')).not.toBeNull()
  })

  it('disables a plan that is not available for the chosen interval', async () => {
    renderPlans()
    await screen.findByText('Pro')

    fireEvent.click(screen.getByRole('button', { name: 'Yearly' }))

    expect(screen.getByText('$190')).not.toBeNull()
    const unavailableButton = screen.getByRole('button', { name: 'Not available' }) as HTMLButtonElement
    expect(unavailableButton.disabled).toBe(true)
  })

  it('reports the selected paid plan and interval in organization mode', async () => {
    const onSelect = vi.fn()
    renderPlans({ mode: 'organization', onSelect })
    await screen.findByText('Pro')

    fireEvent.click(screen.getByRole('button', { name: 'Start free trial' }))

    expect(onSelect).toHaveBeenCalledWith('pro', 'monthly')
    expect(screen.queryByRole('button', { name: 'Get started' })).toBeNull()
  })
})
