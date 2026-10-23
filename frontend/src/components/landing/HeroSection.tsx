import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useBrandName } from '@/hooks/useBrandName'

export function HeroSection() {
  const { t } = useTranslation('landing')
  const brandName = useBrandName()

  return (
    <section className="mx-auto max-w-6xl px-4 pt-16 pb-12 md:pt-24 md:pb-16">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-end lg:gap-16">
        <h1 className="text-[clamp(2.5rem,6vw,4.25rem)] leading-[1.02] font-bold tracking-tight text-balance text-foreground">
          {t('landing:hero.title', { brandName })}
        </h1>
        <div className="space-y-6 lg:pb-2">
          <p className="max-w-[46ch] text-lg leading-relaxed text-pretty text-muted-foreground">
            {t('landing:hero.subtitle')}
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="h-11 px-6 text-base">
              <Link to="/register">{t('landing:hero.primaryCta')}</Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="h-11 px-6 text-base">
              <a href="#features">{t('landing:hero.secondaryCta')}</a>
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">{t('landing:hero.stack')}</p>
        </div>
      </div>
    </section>
  )
}
