import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { notificationService } from '@/services/notificationService'

const UNREAD_COUNT_POLL_INTERVAL_MS = 60_000

interface NotificationsContextValue {
  unreadCount: number
  refreshUnreadCount: () => void
}

const NotificationsContext = createContext<NotificationsContextValue | null>(null)

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [unreadCount, setUnreadCount] = useState(0)
  const [refreshCounter, setRefreshCounter] = useState(0)
  const refreshUnreadCount = useCallback(() => setRefreshCounter((counter) => counter + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    notificationService.getUnreadCount(controller.signal).then(
      (count) => setUnreadCount(count),
      () => {
        // The bell is a hint; a failed poll keeps the last known count.
      },
    )
    return () => controller.abort()
  }, [refreshCounter])

  useEffect(() => {
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') refreshUnreadCount()
    }
    const intervalId = window.setInterval(refreshWhenVisible, UNREAD_COUNT_POLL_INTERVAL_MS)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      window.clearInterval(intervalId)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
  }, [refreshUnreadCount])

  const value = useMemo(() => ({ unreadCount, refreshUnreadCount }), [unreadCount, refreshUnreadCount])
  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>
}

export function useNotifications(): NotificationsContextValue {
  const context = useContext(NotificationsContext)
  if (!context) throw new Error('useNotifications must be used inside NotificationsProvider')
  return context
}
