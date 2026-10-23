import { useTranslation } from 'react-i18next'
import { ConfirmActionDialog } from '@/components/organizations/ConfirmActionDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { InvitableRole, Member } from '@/types/api'

interface MembersTableProps {
  members: Member[]
  currentUserId: string | null
  canManageMembers: boolean
  onRoleChange: (member: Member, role: InvitableRole) => Promise<void>
  onRemove: (member: Member) => Promise<void>
}

export function MembersTable({ members, currentUserId, canManageMembers, onRoleChange, onRemove }: MembersTableProps) {
  const { t } = useTranslation('organizations')

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t('members.columns.member')}</TableHead>
            <TableHead>{t('members.columns.role')}</TableHead>
            <TableHead className="hidden sm:table-cell">{t('members.columns.joined')}</TableHead>
            <TableHead className="text-right">
              <span className="sr-only">{t('members.columns.actions')}</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.map((member) => {
            const displayName = member.full_name || member.email
            const isCurrentUser = member.user_id === currentUserId
            const isOwner = member.role === 'owner'
            const canEditRole = canManageMembers && !isOwner
            const canRemove = !isOwner && (canManageMembers || isCurrentUser)
            const removeLabel = isCurrentUser ? t('members.leave') : t('members.remove')

            return (
              <TableRow key={member.id}>
                <TableCell>
                  <div className="font-medium">
                    {displayName}
                    {isCurrentUser && <span className="ml-2 text-xs text-muted-foreground">{t('members.you')}</span>}
                  </div>
                  {member.full_name && <div className="text-sm text-muted-foreground">{member.email}</div>}
                </TableCell>
                <TableCell>
                  {canEditRole ? (
                    <Select
                      value={member.role}
                      onValueChange={(role) => void onRoleChange(member, role as InvitableRole)}
                    >
                      <SelectTrigger className="w-32" aria-label={t('members.roleLabel', { name: displayName })}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">{t('roles.admin')}</SelectItem>
                        <SelectItem value="member">{t('roles.member')}</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <Badge variant={isOwner ? 'default' : 'secondary'}>{t(`roles.${member.role}`)}</Badge>
                  )}
                </TableCell>
                <TableCell className="hidden text-sm text-muted-foreground sm:table-cell">
                  {new Date(member.joined_at).toLocaleDateString()}
                </TableCell>
                <TableCell className="text-right">
                  {canRemove && (
                    <ConfirmActionDialog
                      trigger={
                        <Button variant="ghost" size="sm">
                          {removeLabel}
                        </Button>
                      }
                      title={isCurrentUser ? t('members.leaveConfirmTitle') : t('members.removeConfirmTitle')}
                      description={
                        isCurrentUser
                          ? t('members.leaveConfirmDescription')
                          : t('members.removeConfirmDescription', { name: displayName })
                      }
                      confirmLabel={removeLabel}
                      onConfirm={() => onRemove(member)}
                    />
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
