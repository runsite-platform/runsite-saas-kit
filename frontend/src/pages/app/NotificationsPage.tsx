import { Bell, CheckCheck, Mail, MailOpen, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { PaginationControls } from '@/components/admin/PaginationControls'
import { NotificationEmailSettingsCard } from '@/components/notifications/NotificationEmailSettingsCard'
import { NotificationItem } from '@/components/notifications/NotificationItem'
import { ConfirmActionDialog } from '@/components/organizations/ConfirmActionDialog'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Button } from '@/components/ui/button'
import { useNotifications } from '@/contexts/NotificationsContext'
import { useApiErrorToast } from '@/hooks/useApiErrorToast'
import { useApiQuery } from '@/hooks/useApiQuery'
import { cn } from '@/lib/utils'
import { notificationService } from '@/services/notificationService'
import type { AppNotification, NotificationReadFilter } from '@/types/api'

const READ_FILTERS: readonly NotificationReadFilter[] = ['all', 'unread', 'read']
const PAGE_SIZE = 20

export default function NotificationsPage() {
  const { t } = useTranslation('notifications')
  const navigate = useNavigate()
  const showApiError = useApiErrorToast()
  const { refreshUnreadCount } = useNotifications()
  const [readFilter, setReadFilter] = useState<NotificationReadFilter>('all')
  const [page, setPage] = useState(1)
  const notificationsQuery = useApiQuery(
    (signal) => notificationService.list({ filter: readFilter, page, pageSize: PAGE_SIZE, signal }),
    [readFilter, page],
  )
  const notificationList = notificationsQuery.data
  const unreadCount = notificationList?.unread_count ?? 0
  const hasNotifications = (notificationList?.total ?? 0) > 0

  const changeFilter = (filter: NotificationReadFilter) => {
    setReadFilter(filter)
    setPage(1)
  }

  const runAction = async (action: () => Promise<unknown>, successMessage?: string) => {
    try {
      await action()
      if (successMessage) toast.success(successMessage)
      notificationsQuery.reload()
      refreshUnreadCount()
    } catch (error) {
      showApiError(error)
    }
  }

  const openNotification = async (notification: AppNotification) => {
    if (!notification.link) return
    if (notification.read_at === null) {
      await runAction(() => notificationService.setRead(notification.id, true))
    }
    navigate(notification.link)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            disabled={unreadCount === 0}
            onClick={() => void runAction(() => notificationService.markAllRead(), t('toast.all_read'))}
          >
            <CheckCheck className="size-4" aria-hidden />
            {t('actions.mark_all_read')}
          </Button>
          <ConfirmActionDialog
            trigger={
              <Button variant="ghost">
                <Trash2 className="size-4" aria-hidden />
                {t('actions.clear_read')}
              </Button>
            }
            title={t('clear_dialog.title')}
            description={t('clear_dialog.description')}
            confirmLabel={t('clear_dialog.confirm')}
            onConfirm={() => runAction(() => notificationService.removeRead(), t('toast.cleared'))}
          />
        </div>
      </div>

      <div className="inline-flex rounded-md border p-0.5" role="group" aria-label={t('filter.label')}>
        {READ_FILTERS.map((filter) => (
          <Button
            key={filter}
            type="button"
            size="sm"
            variant={filter === readFilter ? 'secondary' : 'ghost'}
            aria-pressed={filter === readFilter}
            onClick={() => changeFilter(filter)}
          >
            {t(`filter.${filter}`)}
            {filter === 'unread' && unreadCount > 0 ? (
              <span className="rounded-full bg-primary px-1.5 text-[11px] leading-4 font-semibold text-primary-foreground tabular-nums">
                {unreadCount}
              </span>
            ) : null}
          </Button>
        ))}
      </div>

      {notificationsQuery.error ? (
        <QueryErrorMessage error={notificationsQuery.error} />
      ) : notificationsQuery.isLoading && !notificationList ? (
        <p className="text-sm text-muted-foreground">{t('loading')}</p>
      ) : !notificationList || !hasNotifications ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-10 text-center">
          <Bell className="size-8 text-muted-foreground/60" aria-hidden />
          <p className="text-sm font-medium">{t(`empty.${readFilter}`)}</p>
          <p className="text-sm text-muted-foreground">{t('empty.hint')}</p>
        </div>
      ) : (
        <div>
          <ul className={cn('divide-y rounded-lg border', notificationsQuery.isLoading && 'opacity-60')}>
            {notificationList.items.map((notification) => {
              const isUnread = notification.read_at === null
              return (
                <li
                  key={notification.id}
                  className={cn('px-4 py-3 transition-colors', isUnread && 'bg-muted/40')}
                >
                  <NotificationItem
                    notification={notification}
                    onOpen={notification.link ? () => void openNotification(notification) : undefined}
                    actions={
                      <>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={isUnread ? t('actions.mark_read') : t('actions.mark_unread')}
                          title={isUnread ? t('actions.mark_read') : t('actions.mark_unread')}
                          onClick={() => void runAction(() => notificationService.setRead(notification.id, isUnread))}
                        >
                          {isUnread ? <MailOpen className="size-4" aria-hidden /> : <Mail className="size-4" aria-hidden />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={t('actions.delete')}
                          title={t('actions.delete')}
                          onClick={() => void runAction(() => notificationService.remove(notification.id))}
                        >
                          <Trash2 className="size-4" aria-hidden />
                        </Button>
                      </>
                    }
                  />
                </li>
              )
            })}
          </ul>
          {notificationList.total > PAGE_SIZE ? (
            <PaginationControls
              page={page}
              pageSize={PAGE_SIZE}
              total={notificationList.total}
              onPageChange={setPage}
            />
          ) : null}
        </div>
      )}

      <NotificationEmailSettingsCard />
    </div>
  )
}
