import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { acceptInvitation, getInvitationPreview } from '@/services/invitationService'
import type { InvitationPreview } from '@/types/api'
import { ApiError } from '@/utils/apiError'
import { clearPendingInvitation, rememberPendingInvitation } from '@/utils/returnPath'

type PreviewState =
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'ready'; preview: InvitationPreview }

export default function AcceptInvitationPage() {
  const { t } = useTranslation('organizations')
  const { token = '' } = useParams()
  const { status: authStatus, user, reloadMe, logout } = useAuth()
  const navigate = useNavigate()
  const [previewState, setPreviewState] = useState<PreviewState>({ status: 'loading' })
  const [acceptError, setAcceptError] = useState<ApiError | null>(null)
  const [isAccepting, setIsAccepting] = useState(false)
  const invitationPath = `/invite/${encodeURIComponent(token)}`

  useEffect(() => {
    const controller = new AbortController()
    getInvitationPreview(token, controller.signal)
      .then((preview) => setPreviewState({ status: 'ready', preview }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted && error instanceof ApiError) {
          setPreviewState({ status: 'error', error })
        }
      })
    return () => controller.abort()
  }, [token])

  useEffect(() => {
    if (authStatus === 'anonymous') {
      rememberPendingInvitation(invitationPath)
    }
    if (authStatus === 'authenticated') {
      clearPendingInvitation()
    }
  }, [authStatus, invitationPath])

  async function acceptCurrentInvitation() {
    setIsAccepting(true)
    setAcceptError(null)
    try {
      const organization = await acceptInvitation(token)
      await reloadMe()
      navigate(`/app/${organization.slug}`, { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setAcceptError(error)
        return
      }
      throw error
    } finally {
      setIsAccepting(false)
    }
  }

  function renderContent() {
    if (previewState.status === 'loading' || authStatus === 'loading') {
      return (
        <CardContent className="py-8">
          <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
        </CardContent>
      )
    }

    if (previewState.status === 'error') {
      return (
        <>
          <CardHeader>
            <CardTitle>{t('acceptInvite.invalidTitle')}</CardTitle>
            <CardDescription>{t('acceptInvite.invalidDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/">{t('acceptInvite.goHome')}</Link>
            </Button>
          </CardContent>
        </>
      )
    }

    const { preview } = previewState
    if (preview.expired) {
      return (
        <CardHeader>
          <CardTitle>{t('acceptInvite.expiredTitle')}</CardTitle>
          <CardDescription>{t('acceptInvite.expiredDescription')}</CardDescription>
        </CardHeader>
      )
    }

    const roleName = t(`roles.${preview.role}`)
    const description = preview.inviter_name
      ? t('acceptInvite.descriptionWithInviter', {
          inviter: preview.inviter_name,
          organization: preview.organization_name,
          role: roleName,
        })
      : t('acceptInvite.description', { organization: preview.organization_name, role: roleName })
    const isEmailMismatch = Boolean(user && user.email.toLowerCase() !== preview.email.toLowerCase())

    return (
      <>
        <CardHeader>
          <CardTitle>{t('acceptInvite.title', { organization: preview.organization_name })}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {authStatus === 'anonymous' && (
            <>
              <p className="text-sm">{t('acceptInvite.signInPrompt', { email: preview.email })}</p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button asChild className="flex-1">
                  <Link to="/login" state={{ from: invitationPath }}>
                    {t('acceptInvite.login')}
                  </Link>
                </Button>
                <Button asChild variant="outline" className="flex-1">
                  <Link to="/register" state={{ from: invitationPath }}>
                    {t('acceptInvite.register')}
                  </Link>
                </Button>
              </div>
            </>
          )}

          {authStatus === 'authenticated' && isEmailMismatch && (
            <>
              <p role="alert" className="text-sm text-destructive">
                {t('acceptInvite.emailMismatch', { invitedEmail: preview.email, currentEmail: user?.email ?? '' })}
              </p>
              <Button variant="outline" className="w-full" onClick={() => void logout()}>
                {t('acceptInvite.switchAccount')}
              </Button>
            </>
          )}

          {authStatus === 'authenticated' && !isEmailMismatch && (
            <Button className="w-full" disabled={isAccepting} onClick={() => void acceptCurrentInvitation()}>
              {isAccepting ? t('acceptInvite.accepting') : t('acceptInvite.accept')}
            </Button>
          )}

          {acceptError && <ApiErrorMessage error={acceptError} />}
        </CardContent>
      </>
    )
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/40 px-4 py-12">
      <Card className="w-full max-w-md">{renderContent()}</Card>
    </div>
  )
}
