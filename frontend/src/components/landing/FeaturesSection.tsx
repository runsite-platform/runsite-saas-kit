import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { KIT_PARTS, type KitPartId } from '@/components/landing/kitParts'
import { ProductPreview } from '@/components/landing/ProductPreview'
import { cn } from '@/lib/utils'

export function FeaturesSection() {
  const { t } = useTranslation('landing')
  const [activePart, setActivePart] = useState<KitPartId>('billing')

  return (
    <section id="features" className="scroll-mt-20 border-y bg-muted/40">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-4 py-14 md:py-20 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-12">
        <div className="min-w-0 lg:sticky lg:top-24 lg:self-start">
          <ProductPreview activePart={activePart} />
        </div>

        <div>
          <h2 className="text-3xl leading-tight font-bold tracking-[-0.02em] text-balance text-foreground">
            {t('landing:features.title')}
          </h2>
          <p className="mt-3 text-pretty text-muted-foreground">{t('landing:features.subtitle')}</p>

          <ul aria-label={t('landing:features.listLabel')} className="mt-6 border-t">
            {KIT_PARTS.map((kitPart) => {
              const isActive = kitPart.id === activePart
              const descriptionId = `kit-part-${kitPart.id}`
              return (
                <li key={kitPart.id} className="border-b">
                  <button
                    type="button"
                    aria-expanded={isActive}
                    aria-controls={descriptionId}
                    onClick={() => setActivePart(kitPart.id)}
                    className={cn(
                      'flex w-full items-center gap-3 py-3 text-left font-medium text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50',
                      isActive && 'text-foreground',
                    )}
                  >
                    <span
                      className={cn(
                        'flex size-8 shrink-0 items-center justify-center rounded-md border bg-background transition-colors',
                        isActive && 'border-highlight bg-highlight text-highlight-foreground',
                      )}
                    >
                      <kitPart.icon className="size-4" aria-hidden="true" />
                    </span>
                    {t(kitPart.titleKey)}
                  </button>
                  <div id={descriptionId} hidden={!isActive}>
                    <p className="pb-4 pl-11 text-sm leading-relaxed text-muted-foreground">{t(kitPart.descriptionKey)}</p>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </section>
  )
}
