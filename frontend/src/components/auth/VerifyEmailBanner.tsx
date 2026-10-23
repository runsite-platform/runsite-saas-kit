import { MailWarning } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { authService } from '@/services/auth'
import { ApiError } from '@/utils/apiError'

type ResendState = 'idle' | 'sending' | 'sent'

export function VerifyEmailBanner() {
  const { t } = useTranslation('auth')
  const { user } = useAuth()
  const [resendState, setResendState] = useState<ResendState>('idle')
  const [resendError, setResendError] = useState<ApiError | null>(null)

  if (!user || user.is_email_verified) {
    return null
  }

  async function resend(email: string) {
    setResendState('sending')
    setResendError(null)
    try {
      await authService.resendVerification(email)
      setResendState('sent')
    } catch (error) {
      setResendState('idle')
      if (error instanceof ApiError) {
        setResendError(error)
        return
      }
      throw error
    }
  }

  return (
    <Alert>
      <MailWarning className="size-4" aria-hidden="true" />
      <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
        <span>{t('banner.message', { email: user.email })}</span>
        {resendState === 'sent' ? (
          <span role="status" className="text-sm">
            {t('banner.sent')}
          </span>
        ) : (
          <Button
            size="sm"
            variant="outline"
            disabled={resendState === 'sending'}
            onClick={() => void resend(user.email)}
          >
            {t('banner.resend')}
          </Button>
        )}
        {resendError ? <ApiErrorMessage error={resendError} /> : null}
      </AlertDescription>
    </Alert>
  )
}
