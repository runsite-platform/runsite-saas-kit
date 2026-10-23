import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { PageLoader } from '@/components/shared/PageLoader'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { authService } from '@/services/auth'

type VerificationResult = 'verifying' | 'success' | 'failed'

export function VerifyEmailPage() {
  const { t } = useTranslation('auth')
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const { status: authStatus, reloadMe } = useAuth()
  const [result, setResult] = useState<VerificationResult>(token ? 'verifying' : 'failed')
  const requestedToken = useRef<string | null>(null)

  useEffect(() => {
    if (!token || requestedToken.current === token) {
      return
    }
    requestedToken.current = token
    authService
      .verifyEmail(token)
      .then(() => setResult('success'))
      .catch(() => setResult('failed'))
  }, [token])

  useEffect(() => {
    if (result === 'success' && authStatus === 'authenticated') {
      reloadMe().catch(() => undefined)
    }
  }, [result, authStatus, reloadMe])

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('verify.title')}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        {result === 'verifying' ? <PageLoader label={t('verify.verifying')} /> : null}
        {result === 'success' ? (
          <Alert>
            <AlertDescription>{t('verify.success')}</AlertDescription>
          </Alert>
        ) : null}
        {result === 'failed' ? (
          <Alert variant="destructive">
            <AlertDescription>{t('verify.failed')}</AlertDescription>
          </Alert>
        ) : null}
        {result !== 'verifying' ? (
          <Button asChild>
            <Link to={authStatus === 'authenticated' ? '/app' : '/login'}>{t('verify.continue')}</Link>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  )
}
