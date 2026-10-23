import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export function ClosingCtaSection() {
  const { t } = useTranslation('landing')

  return (
    <section className="px-4 pb-20">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 rounded-3xl bg-primary px-6 py-12 text-primary-foreground md:flex-row md:items-end md:justify-between md:px-12 md:py-16">
        <div className="max-w-xl">
          <h2 className="text-3xl leading-tight font-bold tracking-[-0.02em] text-balance md:text-5xl">
            {t('landing:cta.title')}
          </h2>
          <p className="mt-4 text-lg text-pretty opacity-85">{t('landing:cta.subtitle')}</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row md:shrink-0">
          <Button
            asChild
            size="lg"
            className="h-11 bg-primary-foreground px-6 text-base text-primary hover:bg-primary-foreground/90"
          >
            <Link to="/register">{t('landing:cta.primary')}</Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="ghost"
            className="h-11 px-6 text-base text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
          >
            <Link to="/login">{t('landing:cta.secondary')}</Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
