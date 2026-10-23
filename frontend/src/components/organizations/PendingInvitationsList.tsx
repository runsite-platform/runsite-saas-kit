import { useTranslation } from 'react-i18next'
import { ConfirmActionDialog } from '@/components/organizations/ConfirmActionDialog'
import { Button } from '@/components/ui/button'
import type { Invitation } from '@/types/api'

interface PendingInvitationsListProps {
  invitations: Invitation[]
  onRevoke: (invitation: Invitation) => Promise<void>
}

export function PendingInvitationsList({ invitations, onRevoke }: PendingInvitationsListProps) {
  const { t } = useTranslation('organizations')

  return (
    <section className="space-y-3" aria-labelledby="pending-invitations-heading">
      <h2 id="pending-invitations-heading" className="text-lg font-semibold">
        {t('invitations.title')}
      </h2>
      {invitations.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('invitations.empty')}</p>
      ) : (
        <ul className="divide-y rounded-lg border">
          {invitations.map((invitation) => (
            <li key={invitation.id} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="truncate font-medium">{invitation.email}</p>
                <p className="text-sm text-muted-foreground">
                  {t(`roles.${invitation.role}`)} ·{' '}
                  {t('invitations.expires', { date: new Date(invitation.expires_at).toLocaleDateString() })}
                </p>
              </div>
              <ConfirmActionDialog
                trigger={
                  <Button variant="ghost" size="sm">
                    {t('invitations.revoke')}
                  </Button>
                }
                title={t('invitations.revokeConfirmTitle')}
                description={t('invitations.revokeConfirmDescription', { email: invitation.email })}
                confirmLabel={t('invitations.revoke')}
                onConfirm={() => onRevoke(invitation)}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
