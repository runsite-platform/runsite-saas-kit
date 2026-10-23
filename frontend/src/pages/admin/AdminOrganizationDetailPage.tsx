import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { PlanOverrideForm } from '@/components/admin/PlanOverrideForm'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApiQuery } from '@/hooks/useApiQuery'
import { getOrganization } from '@/services/adminService'
import { billingService } from '@/services/billing'
import { formatCents } from '@/utils/billingFormat'
import { formatShortDate } from '@/utils/statsFormatting'

export function AdminOrganizationDetailPage() {
  const { t, i18n } = useTranslation('admin')
  const { organizationId = '' } = useParams()
  const detail = useApiQuery((signal) => getOrganization(organizationId, signal), [organizationId])
  const plans = useApiQuery((signal) => billingService.listPlans(signal), [])

  if (!detail.data) {
    return detail.isLoading ? (
      <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
    ) : (
      <QueryErrorMessage error={detail.error} />
    )
  }

  const organization = detail.data
  const subscription = organization.subscription
  const optionalDate = (value: string | null) => (value ? formatShortDate(value, i18n.language) : t('common.not_set'))

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/admin/organizations">
          <ArrowLeft className="size-4" aria-hidden="true" />
          {t('common.back')}
        </Link>
      </Button>

      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{organization.name}</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>{organization.slug}</span>
          <Badge variant="secondary">{t(`plans.${organization.plan_id}`, { defaultValue: organization.plan_id })}</Badge>
          {organization.plan_override_id ? <Badge variant="outline">{t('organizations.override_badge')}</Badge> : null}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t('organizations.detail.subscription')}</CardTitle>
          </CardHeader>
          <CardContent>
            {subscription ? (
              <dl className="grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">{t('organizations.detail.provider')}</dt>
                  <dd>{subscription.provider}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('organizations.detail.status')}</dt>
                  <dd>{subscription.status}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('organizations.columns.plan')}</dt>
                  <dd>{t(`plans.${subscription.plan_id}`, { defaultValue: subscription.plan_id })}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('organizations.detail.interval')}</dt>
                  <dd>{subscription.interval}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('organizations.detail.period_end')}</dt>
                  <dd>{optionalDate(subscription.current_period_end)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('organizations.detail.trial_ends')}</dt>
                  <dd>{optionalDate(subscription.trial_ends_at)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t('organizations.detail.cancel_at_period_end')}</dt>
                  <dd>{subscription.cancel_at_period_end ? t('common.yes') : t('common.no')}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">{t('organizations.detail.no_subscription')}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('organizations.override.title')}</CardTitle>
            <CardDescription>{t('organizations.override.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <QueryErrorMessage error={plans.error} />
            {plans.data ? (
              <PlanOverrideForm
                key={organization.plan_override_id ?? 'none'}
                organization={organization}
                plans={plans.data}
                onSaved={detail.reload}
              />
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Card className="py-0">
        <CardHeader className="pt-6">
          <CardTitle>{t('organizations.detail.members')}</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('users.columns.email')}</TableHead>
                <TableHead>{t('users.columns.name')}</TableHead>
                <TableHead>{t('users.columns.role')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {organization.members.map((member) => (
                <TableRow key={member.membership_id}>
                  <TableCell>
                    <Link className="font-medium underline-offset-4 hover:underline" to={`/admin/users/${member.user_id}`}>
                      {member.email}
                    </Link>
                  </TableCell>
                  <TableCell>{member.full_name || t('common.not_set')}</TableCell>
                  <TableCell>{t(`org_roles.${member.role}`, { defaultValue: member.role })}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="py-0">
        <CardHeader className="pt-6">
          <CardTitle>{t('organizations.detail.payments')}</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {organization.payments.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-muted-foreground">{t('organizations.detail.no_payments')}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('organizations.detail.paid_at')}</TableHead>
                  <TableHead className="text-right">{t('organizations.detail.amount')}</TableHead>
                  <TableHead>{t('organizations.detail.status')}</TableHead>
                  <TableHead>{t('organizations.detail.invoice')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {organization.payments.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell className="tabular-nums">{optionalDate(payment.paid_at)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCents(payment.amount_cents, payment.currency, i18n.language)}
                    </TableCell>
                    <TableCell>{payment.status}</TableCell>
                    <TableCell>
                      {payment.invoice_url ? (
                        <a className="underline underline-offset-4" href={payment.invoice_url} target="_blank" rel="noreferrer">
                          {t('organizations.detail.open_invoice')}
                        </a>
                      ) : (
                        t('common.not_set')
                      )}
                    </TableCell>
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
