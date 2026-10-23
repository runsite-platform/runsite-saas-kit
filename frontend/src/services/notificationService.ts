import type {
  AppNotification,
  NotificationEmailSetting,
  NotificationList,
  NotificationReadFilter,
  NotificationSettings,
} from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

const NOTIFICATIONS_PATH = '/me/notifications'

export interface NotificationListParams {
  filter?: NotificationReadFilter
  page?: number
  pageSize?: number
  signal?: AbortSignal
}

export const notificationService = {
  list({ filter = 'all', page = 1, pageSize = 20, signal }: NotificationListParams = {}): Promise<NotificationList> {
    const query = new URLSearchParams({ filter, page: String(page), size: String(pageSize) })
    return fetchApi<NotificationList>(`${NOTIFICATIONS_PATH}?${query}`, { signal })
  },

  async getUnreadCount(signal?: AbortSignal): Promise<number> {
    const response = await fetchApi<{ unread_count: number }>(`${NOTIFICATIONS_PATH}/unread-count`, { signal })
    return response.unread_count
  },

  setRead(notificationId: string, isRead: boolean): Promise<AppNotification> {
    return fetchApi<AppNotification>(`${NOTIFICATIONS_PATH}/${notificationId}`, {
      method: 'PATCH',
      body: { is_read: isRead },
    })
  },

  markAllRead(): Promise<void> {
    return fetchApi<void>(`${NOTIFICATIONS_PATH}/read-all`, { method: 'POST' })
  },

  remove(notificationId: string): Promise<void> {
    return fetchApi<void>(`${NOTIFICATIONS_PATH}/${notificationId}`, { method: 'DELETE' })
  },

  removeRead(): Promise<void> {
    return fetchApi<void>(`${NOTIFICATIONS_PATH}/read`, { method: 'DELETE' })
  },

  getSettings(signal?: AbortSignal): Promise<NotificationSettings> {
    return fetchApi<NotificationSettings>(`${NOTIFICATIONS_PATH}/settings`, { signal })
  },

  updateSettings(settings: NotificationEmailSetting[]): Promise<NotificationSettings> {
    return fetchApi<NotificationSettings>(`${NOTIFICATIONS_PATH}/settings`, { method: 'PUT', body: { settings } })
  },
}
