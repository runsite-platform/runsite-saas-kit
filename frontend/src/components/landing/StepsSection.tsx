import { useTranslation } from 'react-i18next'

const STEP_ITEMS = [
  { titleKey: 'landing:steps.deploy.title', descriptionKey: 'landing:steps.deploy.description' },
  { titleKey: 'landing:steps.brand.title', descriptionKey: 'landing:steps.brand.description' },
  { titleKey: 'landing:steps.build.title', descriptionKey: 'landing:steps.build.description' },
] as const

export function StepsSection() {
  const { t } = useTranslation('landing')

  return (
    <section id="how-it-works" className="scroll-mt-20">
      <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
        <div className="max-w-2xl">
          <h2 className="text-3xl leading-tight font-bold tracking-[-0.02em] text-balance text-foreground md:text-4xl">
            {t('landing:steps.title')}
          </h2>
          <p className="mt-3 text-pretty text-muted-foreground">{t('landing:steps.subtitle')}</p>
        </div>
        <ol className="mt-12 grid gap-10 md:grid-cols-3 md:gap-8">
          {STEP_ITEMS.map((stepItem, stepIndex) => (
            <li key={stepItem.titleKey} className="border-t-2 border-foreground pt-5">
              <span className="text-5xl leading-none font-extrabold text-primary tabular-nums" aria-hidden="true">
                {stepIndex + 1}
              </span>
              <h3 className="mt-4 text-lg font-semibold text-foreground">{t(stepItem.titleKey)}</h3>
              <p className="mt-2 max-w-[38ch] text-pretty text-muted-foreground">{t(stepItem.descriptionKey)}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
