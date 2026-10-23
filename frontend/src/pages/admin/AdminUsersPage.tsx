import { useState, type FormEvent } from 'react'
import { Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { PaginationControls } from '@/components/admin/PaginationControls'
import { PlatformRoleBadge, UserStatusBadges } from '@/components/admin/UserBadges'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useApiQuery } from '@/hooks/useApiQuery'
import { listUsers } from '@/services/adminService'
import { buildListParams, parsePage } from '@/utils/listParams'
import { formatShortDate } from '@/utils/statsFormatting'

const PAGE_SIZE = 20

export function AdminUsersPage() {
  const { t, i18n } = useTranslation('admin')
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') ?? ''
  const page = parsePage(searchParams.get('page'))
  const [searchDraft, setSearchDraft] = useState(search)
  const users = useApiQuery((signal) => listUsers({ search, page, pageSize: PAGE_SIZE }, signal), [search, page])

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSearchParams(buildListParams({ search: searchDraft.trim(), page: 1 }))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('users.title')}</h1>
      <form onSubmit={submitSearch} className="flex max-w-md gap-2" role="search">
        <Input
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={t('users.search_placeholder')}
          aria-label={t('users.search_placeholder')}
          maxLength={200}
        />
        <Button type="submit" variant="secondary">
          <Search className="size-4" aria-hidden="true" />
          {t('common.search')}
        </Button>
      </form>
      <QueryErrorMessage error={users.error} />
      <Card className="py-0">
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('users.columns.email')}</TableHead>
                <TableHead>{t('users.columns.name')}</TableHead>
                <TableHead>{t('users.columns.role')}</TableHead>
                <TableHead>{t('users.columns.status')}</TableHead>
                <TableHead>{t('users.columns.joined')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.data?.items.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <Link className="font-medium underline-offset-4 hover:underline" to={`/admin/users/${user.id}`}>
                      {user.email}
                    </Link>
                  </TableCell>
                  <TableCell>{user.full_name || t('common.not_set')}</TableCell>
                  <TableCell>
                    <PlatformRoleBadge role={user.platform_role} />
                  </TableCell>
                  <TableCell>
                    <UserStatusBadges user={user} />
                  </TableCell>
                  <TableCell className="tabular-nums">{formatShortDate(user.created_at, i18n.language)}</TableCell>
                </TableRow>
              ))}
              {users.data && users.data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                    {t('common.empty')}
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      {users.data ? (
        <PaginationControls
          page={page}
          pageSize={PAGE_SIZE}
          total={users.data.total}
          onPageChange={(nextPage) => setSearchParams(buildListParams({ search, page: nextPage }))}
        />
      ) : null}
    </div>
  )
}
