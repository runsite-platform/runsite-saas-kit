import { useTranslation } from 'react-i18next'

interface SectionPlaceholderPageProps {
  titleKey: string
}

export default function SectionPlaceholderPage({ titleKey }: SectionPlaceholderPageProps) {
  const { t } = useTranslation('organizations')

  return (
    <div className="space-y-2">
      <h1 className="text-2xl font-semibold">{t(titleKey)}</h1>
      <p className="text-muted-foreground">{t('placeholder.description')}</p>
    </div>
  )
}
