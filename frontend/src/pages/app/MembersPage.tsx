import { UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { InviteMemberDialog } from '@/components/organizations/InviteMemberDialog'
import { MembersTable } from '@/components/organizations/MembersTable'
import { PendingInvitationsList } from '@/components/organizations/PendingInvitationsList'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { listInvitations, revokeInvitation } from '@/services/invitationService'
import { changeMemberRole, listMembers, removeMember } from '@/services/memberService'
import { getOrganization } from '@/services/organizationService'
import type { InvitableRole, Invitation, Member, OrganizationDetail } from '@/types/api'
import { ApiError } from '@/utils/apiError'

interface MembersPageData {
  members: Member[]
  invitations: Invitation[]
  detail: OrganizationDetail
}

export default function MembersPage() {
  const { t } = useTranslation('organizations')
  const { organization, can } = useCurrentOrganization()
  const { user, reloadMe } = useAuth()
  const navigate = useNavigate()
  const canManageMembers = can('manage_members')
  const [pageData, setPageData] = useState<MembersPageData | null>(null)
  const [loadError, setLoadError] = useState<ApiError | null>(null)
  const [actionError, setActionError] = useState<ApiError | null>(null)
  const [reloadCounter, setReloadCounter] = useState(0)
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      listMembers(organization.id, controller.signal),
      canManageMembers ? listInvitations(organization.id, controller.signal) : Promise.resolve<Invitation[]>([]),
      getOrganization(organization.id, controller.signal),
    ])
      .then(([members, invitations, detail]) => {
        setPageData({ members, invitations, detail })
        setLoadError(null)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        if (error instanceof ApiError) {
          setLoadError(error)
        }
      })
    return () => controller.abort()
  }, [organization.id, canManageMembers, reloadCounter])

  const reloadPageData = () => setReloadCounter((counter) => counter + 1)

  async function runAction(action: () => Promise<void>) {
    setActionError(null)
    try {
      await action()
    } catch (error) {
      if (error instanceof ApiError) {
        setActionError(error)
        return
      }
      throw error
    }
  }

  const handleRoleChange = (member: Member, role: InvitableRole) =>
    runAction(async () => {
      await changeMemberRole(organization.id, member.id, role)
      reloadPageData()
    })

  const handleRemove = (member: Member) =>
    runAction(async () => {
      await removeMember(organization.id, member.id)
      if (member.user_id === user?.id) {
        await reloadMe()
        navigate('/app', { replace: true })
        return
      }
      reloadPageData()
    })

  const handleRevoke = (invitation: Invitation) =>
    runAction(async () => {
      await revokeInvitation(organization.id, invitation.id)
      reloadPageData()
    })

  if (loadError) {
    return <ApiErrorMessage error={loadError} />
  }
  if (!pageData) {
    return <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
  }

  const { members, invitations, detail } = pageData
  const usedSeats = detail.member_count + detail.pending_invitation_count

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t('members.title')}</h1>
          <p className="text-sm text-muted-foreground">
            {t('members.seats', { used: usedSeats, limit: detail.limits.members })}
          </p>
        </div>
        {canManageMembers && (
          <Button onClick={() => setIsInviteDialogOpen(true)}>
            <UserPlus className="size-4" aria-hidden />
            {t('members.inviteButton')}
          </Button>
        )}
      </div>

      {actionError && <ApiErrorMessage error={actionError} />}

      <MembersTable
        members={members}
        currentUserId={user?.id ?? null}
        canManageMembers={canManageMembers}
        onRoleChange={handleRoleChange}
        onRemove={handleRemove}
      />

      {canManageMembers && <PendingInvitationsList invitations={invitations} onRevoke={handleRevoke} />}

      {canManageMembers && (
        <InviteMemberDialog
          memberLimit={detail.limits.members}
          open={isInviteDialogOpen}
          onOpenChange={setIsInviteDialogOpen}
          onInvited={reloadPageData}
        />
      )}
    </div>
  )
}
