import { useTranslation } from 'react-i18next'
import { Navigate } from 'react-router-dom'
import { PageLoader } from '@/components/shared/PageLoader'
import { useAuth } from '@/contexts/AuthContext'

export function AuthCallbackPage() {
  const { t } = useTranslation('auth')
  const { status } = useAuth()
  if (status === 'loading') {
    return <PageLoader label={t('callback.signing_in')} />
  }
  if (status === 'authenticated') {
    return <Navigate to="/app" replace />
  }
  return <Navigate to="/login?error=oauth_failed" replace />
}
