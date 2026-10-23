import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import '@/i18n'
import { UpgradeDialog } from '@/components/billing/UpgradeDialog'
import { emitPlanUpgradeRequired } from '@/utils/apiEvents'

function renderInOrganization() {
  return render(
    <MemoryRouter initialEntries={['/app/acme/projects']}>
      <Routes>
        <Route path="/app/:orgSlug/projects" element={<UpgradeDialog />} />
        <Route path="/app/:orgSlug/billing" element={<p>billing page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('UpgradeDialog', () => {
  afterEach(() => cleanup())

  it('opens on plan-upgrade-required and links to the billing page', async () => {
    renderInOrganization()
    expect(screen.queryByRole('dialog')).toBeNull()

    act(() => emitPlanUpgradeRequired({ feature: 'analytics', required_plan: 'pro' }))

    expect(await screen.findByText('Analytics charts is part of the Pro plan.')).not.toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'View plans' }))
    expect(await screen.findByText('billing page')).not.toBeNull()
  })
})
