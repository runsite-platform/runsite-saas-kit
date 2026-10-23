import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { formatRelativeTime, notificationKindStyle } from '@/components/notifications/notificationKinds'
import { cn } from '@/lib/utils'
import type { AppNotification } from '@/types/api'

interface NotificationItemProps {
  notification: AppNotification
  compact?: boolean
  actions?: ReactNode
  onOpen?: () => void
}

export function NotificationItem({ notification, compact = false, actions, onOpen }: NotificationItemProps) {
  const { t, i18n } = useTranslation('notifications')
  const { icon: KindIcon, toneClassName } = notificationKindStyle(notification.kind)
  const isUnread = notification.read_at === null

  return (
    <div className="flex w-full min-w-0 items-start gap-3">
      <span
        className={cn('flex shrink-0 items-center justify-center rounded-full', toneClassName, compact ? 'size-8' : 'size-9')}
        aria-hidden
      >
        <KindIcon className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          {onOpen ? (
            <button
              type="button"
              onClick={onOpen}
              className={cn(
                'min-w-0 truncate text-left text-sm underline-offset-4 outline-none hover:underline focus-visible:underline',
                isUnread ? 'font-semibold' : 'font-medium text-foreground/80',
              )}
            >
              {notification.title}
            </button>
          ) : (
            <p className={cn('min-w-0 truncate text-sm', isUnread ? 'font-semibold' : 'font-medium text-foreground/80')}>
              {notification.title}
            </p>
          )}
          {isUnread ? (
            <span className="size-2 shrink-0 rounded-full bg-primary">
              <span className="sr-only">{t('unread')}</span>
            </span>
          ) : null}
        </div>
        {notification.body ? (
          <p className={cn('text-sm text-muted-foreground', compact ? 'line-clamp-1' : 'line-clamp-2')}>
            {notification.body}
          </p>
        ) : null}
        <time dateTime={notification.created_at} className="text-xs text-muted-foreground">
          {formatRelativeTime(notification.created_at, i18n.language)}
        </time>
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-1">{actions}</div> : null}
    </div>
  )
}
