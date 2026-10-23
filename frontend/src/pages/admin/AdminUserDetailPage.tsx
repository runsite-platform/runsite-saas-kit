import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PlatformRoleBadge, UserStatusBadges } from '@/components/admin/UserBadges'
import { ConfirmActionDialog } from '@/components/organizations/ConfirmActionDialog'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAuth } from '@/contexts/AuthContext'
import { useApiQuery } from '@/hooks/useApiQuery'
import {
  blockUser,
  getUser,
  grantAdmin,
  impersonateUser,
  resendVerification,
  revokeAdmin,
  unblockUser,
} from '@/services/adminService'
import { isSuperadmin } from '@/utils/platformRoles'
import { formatShortDate } from '@/utils/statsFormatting'

type UserAction = 'block' | 'unblock' | 'resend' | 'grant' | 'revoke' | 'impersonate'

export function AdminUserDetailPage() {
  const { t, i18n } = useTranslation('admin')
  const { userId = '' } = useParams()
  const navigate = useNavigate()
  const { user: currentUser, impersonatedBy, acceptAccessToken } = useAuth()
  const detail = useApiQuery((signal) => getUser(userId, signal), [userId])
  const [pendingAction, setPendingAction] = useState<UserAction | null>(null)
  const [actionError, setActionError] = useState<unknown>(null)
  const [notice, setNotice] = useState<string | null>(null)

  async function runAction(action: UserAction, request: () => Promise<string | null>) {
    setPendingAction(action)
    setActionError(null)
    setNotice(null)
    try {
      setNotice(await request())
      detail.reload()
    } catch (error) {
      setActionError(error)
    } finally {
      setPendingAction(null)
    }
  }

  async function startImpersonation() {
    setPendingAction('impersonate')
    setActionError(null)
    try {
      const impersonation = await impersonateUser(userId)
      await acceptAccessToken(impersonation.access_token)
      navigate('/app', { replace: true })
    } catch (error) {
      setActionError(error)
      setPendingAction(null)
    }
  }

  if (!detail.data) {
    return detail.isLoading ? (
      <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
    ) : (
      <QueryErrorMessage error={detail.error} />
    )
  }

  const target = detail.data
  const actorIsSuperadmin = isSuperadmin(currentUser, impersonatedBy)
  const targetIsSuperadmin = target.platform_role === 'superadmin'
  const canModerate =
    currentUser?.id !== target.id && !targetIsSuperadmin && (target.platform_role !== 'admin' || actorIsSuperadmin)
  const canChangeRole = actorIsSuperadmin && !targetIsSuperadmin
  const canImpersonate = actorIsSuperadmin && !targetIsSuperadmin && !target.is_blocked
  const isBusy = pendingAction !== null

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/admin/users">
          <ArrowLeft className="size-4" aria-hidden="true" />
          {t('common.back')}
        </Link>
      </Button>

      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight break-all">{target.email}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <PlatformRoleBadge role={target.platform_role} />
          <UserStatusBadges user={target} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent>
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">{t('users.columns.name')}</dt>
                <dd>{target.full_name || t('common.not_set')}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('users.detail.joined')}</dt>
                <dd>{formatShortDate(target.created_at, i18n.language)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('users.detail.last_login')}</dt>
                <dd>
                  {target.last_login_at ? formatShortDate(target.last_login_at, i18n.language) : t('common.never')}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('users.detail.password')}</dt>
                <dd>{target.has_password ? t('common.yes') : t('common.no')}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t('users.detail.google')}</dt>
                <dd>{target.google_linked ? t('common.yes') : t('common.no')}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('users.detail.actions')}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {canModerate && !target.is_blocked ? (
              <ConfirmActionDialog
                trigger={
                  <Button variant="destructive" disabled={isBusy}>
                    {t('users.actions.block')}
                  </Button>
                }
                title={t('users.actions.block')}
                description={t('users.confirm.block', { email: target.email })}
                confirmLabel={t('users.actions.block')}
                onConfirm={() =>
                  runAction('block', async () => {
                    await blockUser(target.id)
                    return t('users.notices.saved')
                  })
                }
              />
            ) : null}
            {canModerate && target.is_blocked ? (
              <Button
                variant="outline"
                disabled={isBusy}
                onClick={() =>
                  void runAction('unblock', async () => {
                    await unblockUser(target.id)
                    return t('users.notices.saved')
                  })
                }
              >
                {t('users.actions.unblock')}
              </Button>
            ) : null}
            {!target.is_email_verified ? (
              <Button
                variant="outline"
                disabled={isBusy}
                onClick={() =>
                  void runAction('resend', async () => {
                    const result = await resendVerification(target.id)
                    return result.sent ? t('users.notices.verification_sent') : t('users.notices.already_verified')
                  })
                }
              >
                {t('users.actions.resend_verification')}
              </Button>
            ) : null}
            {canChangeRole ? (
              <Button
                variant="outline"
                disabled={isBusy}
                onClick={() =>
                  void runAction(target.platform_role === 'admin' ? 'revoke' : 'grant', async () => {
                    await (target.platform_role === 'admin' ? revokeAdmin(target.id) : grantAdmin(target.id))
                    return t('users.notices.saved')
                  })
                }
              >
                {target.platform_role === 'admin' ? t('users.actions.revoke_admin') : t('users.actions.grant_admin')}
              </Button>
            ) : null}
            {canImpersonate ? (
              <ConfirmActionDialog
                trigger={
                  <Button variant="secondary" disabled={isBusy}>
                    {t('users.actions.impersonate')}
                  </Button>
                }
                title={t('users.actions.impersonate')}
                description={t('users.confirm.impersonate', { email: target.email })}
                confirmLabel={t('users.actions.impersonate')}
                onConfirm={startImpersonation}
              />
            ) : null}
            {notice ? (
              <p role="status" className="text-sm text-muted-foreground">
                {notice}
              </p>
            ) : null}
            <QueryErrorMessage error={actionError} />
          </CardContent>
        </Card>
      </div>

      <Card className="py-0">
        <CardHeader className="pt-6">
          <CardTitle>{t('users.detail.memberships')}</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {target.memberships.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-muted-foreground">{t('users.detail.no_memberships')}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('organizations.columns.name')}</TableHead>
                  <TableHead>{t('organizations.columns.slug')}</TableHead>
                  <TableHead>{t('users.columns.role')}</TableHead>
                  <TableHead>{t('organizations.columns.plan')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {target.memberships.map((membership) => (
                  <TableRow key={membership.organization_id}>
                    <TableCell>
                      <Link
                        className="font-medium underline-offset-4 hover:underline"
                        to={`/admin/organizations/${membership.organization_id}`}
                      >
                        {membership.organization_name}
                      </Link>
                    </TableCell>
                    <TableCell>{membership.organization_slug}</TableCell>
                    <TableCell>{t(`org_roles.${membership.role}`, { defaultValue: membership.role })}</TableCell>
                    <TableCell>{t(`plans.${membership.plan_id}`, { defaultValue: membership.plan_id })}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
