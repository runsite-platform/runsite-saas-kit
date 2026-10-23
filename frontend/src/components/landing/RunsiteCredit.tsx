import { useTranslation } from 'react-i18next'
import { brand } from '@/config/brand'

export function RunsiteCredit() {
  const { t } = useTranslation('landing')

  return (
    <a
      href={brand.runsiteUrl}
      target="_blank"
      rel="noopener"
      className="text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
    >
      {t('landing:credit.deployedOn')}
    </a>
  )
}
