import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import type { User } from '@/types/api'

export function LinkedAccountsSection({ user }: { user: User }) {
  const { t } = useTranslation('account')
  const { features } = usePublicConfig()
  if (!features.google_login && !user.google_linked) {
    return null
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('linked.title')}</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <span className="font-medium">{t('linked.google')}</span>
        <span className={user.google_linked ? 'text-sm' : 'text-sm text-muted-foreground'}>
          {user.google_linked ? t('linked.linked') : t('linked.not_linked')}
        </span>
      </CardContent>
    </Card>
  )
}
