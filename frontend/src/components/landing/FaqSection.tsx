import { Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface FaqItem {
  questionKey: string
  answerKey: string
}

const FAQ_ITEMS: readonly FaqItem[] = [
  {
    questionKey: 'landing:faq.items.whatIsIncluded.question',
    answerKey: 'landing:faq.items.whatIsIncluded.answer',
  },
  { questionKey: 'landing:faq.items.trial.question', answerKey: 'landing:faq.items.trial.answer' },
  { questionKey: 'landing:faq.items.cancel.question', answerKey: 'landing:faq.items.cancel.answer' },
  { questionKey: 'landing:faq.items.dataSafety.question', answerKey: 'landing:faq.items.dataSafety.answer' },
  { questionKey: 'landing:faq.items.team.question', answerKey: 'landing:faq.items.team.answer' },
]

export function FaqSection() {
  const { t } = useTranslation('landing')

  return (
    <section id="faq" className="scroll-mt-20 border-t">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 md:py-24 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <h2 className="text-3xl leading-tight font-bold tracking-[-0.02em] text-balance text-foreground md:text-4xl">
          {t('landing:faq.title')}
        </h2>
        <div className="border-t">
          {FAQ_ITEMS.map((faqItem) => (
            <details key={faqItem.questionKey} className="group border-b">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-5 text-lg font-medium text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 [&::-webkit-details-marker]:hidden">
                {t(faqItem.questionKey)}
                <Plus
                  className="size-5 shrink-0 text-muted-foreground transition-transform duration-200 group-open:rotate-45 motion-reduce:transition-none"
                  aria-hidden="true"
                />
              </summary>
              <p className="max-w-[60ch] pb-5 leading-relaxed text-pretty text-muted-foreground">{t(faqItem.answerKey)}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}
