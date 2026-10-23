import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { useApiErrorToast } from '@/hooks/useApiErrorToast'
import { useApiQuery } from '@/hooks/useApiQuery'
import { notificationService } from '@/services/notificationService'
import type { NotificationEmailSetting, NotificationKind } from '@/types/api'

export function NotificationEmailSettingsCard() {
  const { t } = useTranslation('notifications')
  const showApiError = useApiErrorToast()
  const settingsQuery = useApiQuery((signal) => notificationService.getSettings(signal), [])
  const [savedSettings, setSavedSettings] = useState<NotificationEmailSetting[] | null>(null)
  const [savingKind, setSavingKind] = useState<NotificationKind | null>(null)
  const emailSettings = savedSettings ?? settingsQuery.data?.settings ?? []

  const toggleEmail = async (kind: NotificationKind, emailEnabled: boolean) => {
    setSavingKind(kind)
    try {
      const response = await notificationService.updateSettings([{ kind, email_enabled: emailEnabled }])
      setSavedSettings(response.settings)
    } catch (error) {
      showApiError(error)
    } finally {
      setSavingKind(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.title')}</CardTitle>
        <CardDescription>{t('settings.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {settingsQuery.data && !settingsQuery.data.email_delivery_available ? (
          <Alert>
            <AlertDescription>{t('settings.email_disabled')}</AlertDescription>
          </Alert>
        ) : null}
        {settingsQuery.error ? (
          <QueryErrorMessage error={settingsQuery.error} />
        ) : settingsQuery.isLoading ? (
          <p className="text-sm text-muted-foreground">{t('loading')}</p>
        ) : (
          <ul className="divide-y">
            {emailSettings.map((setting) => {
              const switchId = `notification-email-${setting.kind}`
              return (
                <li key={setting.kind} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                  <label htmlFor={switchId} className="min-w-0 cursor-pointer">
                    <span className="block text-sm font-medium">{t(`kinds.${setting.kind}.label`)}</span>
                    <span className="block text-sm text-muted-foreground">{t(`kinds.${setting.kind}.description`)}</span>
                  </label>
                  <Switch
                    id={switchId}
                    checked={setting.email_enabled}
                    disabled={savingKind === setting.kind}
                    onCheckedChange={(checked) => void toggleEmail(setting.kind, checked)}
                  />
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
