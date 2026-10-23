import { useState, type FormEvent } from 'react'
import { Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { NativeSelect } from '@/components/admin/NativeSelect'
import { PaginationControls } from '@/components/admin/PaginationControls'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApiQuery } from '@/hooks/useApiQuery'
import { listOrganizations } from '@/services/adminService'
import { billingService } from '@/services/billing'
import { buildListParams, parsePage } from '@/utils/listParams'
import { formatShortDate } from '@/utils/statsFormatting'

const PAGE_SIZE = 20

export function AdminOrganizationsPage() {
  const { t, i18n } = useTranslation('admin')
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') ?? ''
  const planId = searchParams.get('plan_id') ?? ''
  const page = parsePage(searchParams.get('page'))
  const [searchDraft, setSearchDraft] = useState(search)
  const organizations = useApiQuery(
    (signal) => listOrganizations({ search, planId, page, pageSize: PAGE_SIZE }, signal),
    [search, planId, page],
  )
  const plans = useApiQuery((signal) => billingService.listPlans(signal), [])

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSearchParams(buildListParams({ search: searchDraft.trim(), plan_id: planId, page: 1 }))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('organizations.title')}</h1>
      <div className="flex flex-wrap items-end gap-4">
        <form onSubmit={submitSearch} className="flex w-full max-w-md gap-2" role="search">
          <Input
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder={t('organizations.search_placeholder')}
            aria-label={t('organizations.search_placeholder')}
            maxLength={200}
          />
          <Button type="submit" variant="secondary">
            <Search className="size-4" aria-hidden="true" />
            {t('common.search')}
          </Button>
        </form>
        <div className="space-y-1">
          <Label htmlFor="organization-plan-filter">{t('organizations.plan_filter')}</Label>
          <NativeSelect
            id="organization-plan-filter"
            value={planId}
            onChange={(event) => setSearchParams(buildListParams({ search, plan_id: event.target.value, page: 1 }))}
          >
            <option value="">{t('organizations.all_plans')}</option>
            {(plans.data ?? []).map((plan) => (
              <option key={plan.id} value={plan.id}>
                {t(`plans.${plan.id}`, { defaultValue: plan.name })}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>
      <QueryErrorMessage error={organizations.error} />
      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('organizations.columns.name')}</TableHead>
                <TableHead>{t('organizations.columns.slug')}</TableHead>
                <TableHead>{t('organizations.columns.plan')}</TableHead>
                <TableHead>{t('organizations.columns.owner')}</TableHead>
                <TableHead className="text-right">{t('organizations.columns.members')}</TableHead>
                <TableHead>{t('organizations.columns.created')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {organizations.data?.items.map((organization) => (
                <TableRow key={organization.id}>
                  <TableCell>
                    <Link
                      className="font-medium underline-offset-4 hover:underline"
                      to={`/admin/organizations/${organization.id}`}
                    >
                      {organization.name}
                    </Link>
                  </TableCell>
                  <TableCell>{organization.slug}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {t(`plans.${organization.plan_id}`, { defaultValue: organization.plan_id })}
                      {organization.plan_override_id ? (
                        <Badge variant="outline">{t('organizations.override_badge')}</Badge>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell>{organization.owner_email ?? t('common.not_set')}</TableCell>
                  <TableCell className="text-right tabular-nums">{organization.members_count}</TableCell>
                  <TableCell className="tabular-nums">
                    {formatShortDate(organization.created_at, i18n.language)}
                  </TableCell>
                </TableRow>
              ))}
              {organizations.data && organizations.data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                    {t('common.empty')}
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      {organizations.data ? (
        <PaginationControls
          page={page}
          pageSize={PAGE_SIZE}
          total={organizations.data.total}
          onPageChange={(nextPage) => setSearchParams(buildListParams({ search, plan_id: planId, page: nextPage }))}
        />
      ) : null}
    </div>
  )
}
