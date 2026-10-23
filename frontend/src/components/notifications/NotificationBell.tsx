import { Bell, CheckCheck } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { NotificationItem } from '@/components/notifications/NotificationItem'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useNotifications } from '@/contexts/NotificationsContext'
import { useApiErrorToast } from '@/hooks/useApiErrorToast'
import { notificationService } from '@/services/notificationService'
import type { AppNotification } from '@/types/api'

const RECENT_NOTIFICATIONS_LIMIT = 6
const MAX_BADGE_COUNT = 99

export function NotificationBell({ notificationsPath }: { notificationsPath: string }) {
  const { t } = useTranslation('notifications')
  const navigate = useNavigate()
  const showApiError = useApiErrorToast()
  const { unreadCount, refreshUnreadCount } = useNotifications()
  const [recentNotifications, setRecentNotifications] = useState<AppNotification[] | null>(null)

  const loadRecentNotifications = async () => {
    try {
      const notificationList = await notificationService.list({ pageSize: RECENT_NOTIFICATIONS_LIMIT })
      setRecentNotifications(notificationList.items)
    } catch (error) {
      showApiError(error)
    }
    refreshUnreadCount()
  }

  const changeOpen = (isOpen: boolean) => {
    if (isOpen) void loadRecentNotifications()
  }

  const openNotification = async (notification: AppNotification) => {
    if (notification.read_at === null) {
      try {
        await notificationService.setRead(notification.id, true)
        refreshUnreadCount()
      } catch (error) {
        showApiError(error)
      }
    }
    navigate(notification.link ?? notificationsPath)
  }

  const markAllRead = async () => {
    try {
      await notificationService.markAllRead()
      const readAt = new Date().toISOString()
      setRecentNotifications((notifications) =>
        notifications?.map((notification) => ({ ...notification, read_at: notification.read_at ?? readAt })) ?? null,
      )
      refreshUnreadCount()
    } catch (error) {
      showApiError(error)
    }
  }

  const badgeLabel = unreadCount > MAX_BADGE_COUNT ? `${MAX_BADGE_COUNT}+` : String(unreadCount)

  return (
    <DropdownMenu onOpenChange={changeOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className="relative"
          aria-label={unreadCount > 0 ? t('bell.label_unread', { count: unreadCount }) : t('bell.label')}
        >
          <Bell className="size-4" aria-hidden />
          {unreadCount > 0 ? (
            <span
              className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] leading-none font-semibold text-white tabular-nums"
              aria-hidden
            >
              {badgeLabel}
            </span>
          ) : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[min(22rem,calc(100vw-2rem))] p-0">
        <div className="flex items-center justify-between gap-2 px-3 py-2">
          <p className="text-sm font-semibold">{t('title')}</p>
          {unreadCount > 0 ? (
            <DropdownMenuItem
              className="h-7 gap-1 px-2 text-xs text-muted-foreground"
              onSelect={(event) => {
                event.preventDefault()
                void markAllRead()
              }}
            >
              <CheckCheck className="size-3.5" aria-hidden />
              {t('actions.mark_all_read')}
            </DropdownMenuItem>
          ) : null}
        </div>
        <DropdownMenuSeparator className="m-0" />
        <div className="max-h-96 overflow-y-auto p-1">
          {recentNotifications === null ? (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">{t('loading')}</p>
          ) : recentNotifications.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-3 py-8 text-center">
              <Bell className="size-6 text-muted-foreground/60" aria-hidden />
              <p className="text-sm text-muted-foreground">{t('empty.all')}</p>
            </div>
          ) : (
            recentNotifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="items-start rounded-md px-2 py-2"
                onSelect={() => void openNotification(notification)}
              >
                <NotificationItem notification={notification} compact />
              </DropdownMenuItem>
            ))
          )}
        </div>
        <DropdownMenuSeparator className="m-0" />
        <DropdownMenuItem asChild className="justify-center rounded-none py-2.5 text-sm font-medium">
          <Link to={notificationsPath}>{t('bell.view_all')}</Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
