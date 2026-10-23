import { useTranslation } from 'react-i18next'
import { PricingPlans } from '@/components/billing/PricingPlans'

export function PricingPage() {
  const { t } = useTranslation('billing')

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-12 md:py-16">
      <header className="mx-auto mb-10 max-w-2xl space-y-3 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-balance md:text-4xl">{t('pricing.title')}</h1>
        <p className="text-muted-foreground text-pretty">{t('pricing.subtitle')}</p>
      </header>
      <PricingPlans mode="public" />
    </div>
  )
}
