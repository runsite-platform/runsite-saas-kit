import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import type { AdminUserSummary } from '@/types/api'

export function PlatformRoleBadge({ role }: { role: string }) {
  const { t } = useTranslation('admin')
  return <Badge variant={role === 'user' ? 'outline' : 'secondary'}>{t(`roles.${role}`, { defaultValue: role })}</Badge>
}

export function UserStatusBadges({ user }: { user: Pick<AdminUserSummary, 'is_blocked' | 'is_email_verified'> }) {
  const { t } = useTranslation('admin')
  return (
    <div className="flex flex-wrap gap-1">
      {user.is_blocked ? <Badge variant="destructive">{t('statuses.blocked')}</Badge> : null}
      {!user.is_email_verified ? <Badge variant="outline">{t('statuses.unverified')}</Badge> : null}
      {!user.is_blocked && user.is_email_verified ? <Badge variant="secondary">{t('statuses.active')}</Badge> : null}
    </div>
  )
}
