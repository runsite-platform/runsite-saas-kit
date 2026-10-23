import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import '@/i18n'
import landing from '@/i18n/locales/en/landing.json'
import { LandingPage } from '@/pages/LandingPage'

afterEach(cleanup)

vi.mock('@/contexts/PublicConfigContext', () => ({
  usePublicConfig: () => ({
    brand_name: 'Testco',
    features: { google_login: false, billing: true, file_uploads: true, email: false },
  }),
}))

// The real PricingPlans needs AuthProvider and the API; it has its own tests in phase 05.
vi.mock('@/components/billing/PricingPlans', () => ({
  PricingPlans: () => <div data-testid="pricing-plans" />,
}))

function renderLandingPage() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  )
}

describe('LandingPage', () => {
  it('shows the hero with the brand name from public config', async () => {
    renderLandingPage()
    const heroHeading = await screen.findByRole('heading', { level: 1 })
    expect(heroHeading.textContent).toContain('Testco')
  })

  it('lists every feature of the kit', async () => {
    renderLandingPage()
    const featureTitles = [
      landing.features.auth.title,
      landing.features.organizations.title,
      landing.features.billing.title,
      landing.features.dashboard.title,
      landing.features.files.title,
      landing.features.admin.title,
      landing.features.modules.title,
      landing.features.theming.title,
    ]
    for (const featureTitle of featureTitles) {
      expect(await screen.findByText(featureTitle)).toBeTruthy()
    }
  })

  it('renders the shared pricing component inside the pricing section', async () => {
    const { container } = renderLandingPage()
    await screen.findByTestId('pricing-plans')
    expect(container.querySelector('#pricing [data-testid="pricing-plans"]')).not.toBeNull()
  })

  it('shows every FAQ question', async () => {
    renderLandingPage()
    for (const faqItem of Object.values(landing.faq.items)) {
      expect(await screen.findByText(faqItem.question)).toBeTruthy()
    }
  })

  it('links registration and the Runsite credit', async () => {
    renderLandingPage()
    const registerLinks = await screen.findAllByRole('link', { name: landing.nav.register })
    expect(registerLinks[0].getAttribute('href')).toBe('/register')
    const creditLink = await screen.findByRole('link', { name: landing.credit.deployedOn })
    expect(creditLink.getAttribute('href')).toBe('https://runsite.app')
  })

  it('never renders a raw translation key', async () => {
    const { container } = renderLandingPage()
    await screen.findByRole('heading', { level: 1 })
    expect(container.textContent).not.toMatch(/\b(nav|hero|features|pricing|faq|footer|credit)\.[a-zA-Z]+/)
  })
})
