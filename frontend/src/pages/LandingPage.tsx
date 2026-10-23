import { useTranslation } from 'react-i18next'
import { PricingPlans } from '@/components/billing/PricingPlans'
import { ClosingCtaSection } from '@/components/landing/ClosingCtaSection'
import { FaqSection } from '@/components/landing/FaqSection'
import { FeaturesSection } from '@/components/landing/FeaturesSection'
import { HeroSection } from '@/components/landing/HeroSection'
import { LandingFooter } from '@/components/landing/LandingFooter'
import { LandingHeader } from '@/components/landing/LandingHeader'
import { StepsSection } from '@/components/landing/StepsSection'

export function LandingPage() {
  const { t } = useTranslation('landing')

  return (
    <div className="min-h-screen bg-background text-foreground">
      <LandingHeader />
      <main>
        <HeroSection />
        <FeaturesSection />
        <StepsSection />
        <section id="pricing" className="scroll-mt-20 border-t bg-muted/40">
          <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
            <div className="mb-10 max-w-2xl">
              <h2 className="text-3xl leading-tight font-bold tracking-[-0.02em] text-balance text-foreground md:text-4xl">
                {t('landing:pricing.title')}
              </h2>
              <p className="mt-3 text-pretty text-muted-foreground">{t('landing:pricing.subtitle')}</p>
            </div>
            <PricingPlans />
          </div>
        </section>
        <FaqSection />
        <ClosingCtaSection />
      </main>
      <LandingFooter />
    </div>
  )
}
