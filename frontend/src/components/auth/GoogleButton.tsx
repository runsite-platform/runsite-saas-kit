import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { GOOGLE_START_URL } from '@/services/auth'

export function GoogleButton() {
  const { t } = useTranslation('auth')
  const { features } = usePublicConfig()
  if (!features.google_login) {
    return null
  }
  return (
    <div className="grid gap-4">
      <Button asChild variant="outline" className="w-full">
        <a href={GOOGLE_START_URL}>{t('google.continue')}</a>
      </Button>
      <div className="flex items-center gap-3 text-xs uppercase text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        {t('google.divider')}
        <span className="h-px flex-1 bg-border" />
      </div>
    </div>
  )
}
