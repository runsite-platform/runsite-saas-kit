import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ConfirmActionDialog } from '@/components/organizations/ConfirmActionDialog'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { listMembers } from '@/services/memberService'
import { transferOwnership } from '@/services/organizationService'
import type { Member } from '@/types/api'
import { ApiError } from '@/utils/apiError'

function memberLabel(member: Member): string {
  return member.full_name ? `${member.full_name} (${member.email})` : member.email
}

export function TransferOwnershipCard() {
  const { t } = useTranslation('organizations')
  const { organization } = useCurrentOrganization()
  const { reloadMe } = useAuth()
  const [candidates, setCandidates] = useState<Member[] | null>(null)
  const [selectedMembershipId, setSelectedMembershipId] = useState('')
  const [transferError, setTransferError] = useState<ApiError | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listMembers(organization.id, controller.signal)
      .then((members) => setCandidates(members.filter((member) => member.role !== 'owner')))
      .catch((error: unknown) => {
        if (!controller.signal.aborted && error instanceof ApiError) {
          setTransferError(error)
        }
      })
    return () => controller.abort()
  }, [organization.id])

  const selectedMember = candidates?.find((member) => member.id === selectedMembershipId) ?? null

  async function confirmTransfer() {
    if (!selectedMember) {
      return
    }
    setTransferError(null)
    try {
      await transferOwnership(organization.id, selectedMember.id)
      await reloadMe()
    } catch (error) {
      if (error instanceof ApiError) {
        setTransferError(error)
        return
      }
      throw error
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.transfer.title')}</CardTitle>
        <CardDescription>{t('settings.transfer.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {candidates === null && !transferError && (
          <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
        )}
        {candidates?.length === 0 && <p className="text-sm text-muted-foreground">{t('settings.transfer.noCandidates')}</p>}
        {candidates && candidates.length > 0 && (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="transfer-ownership-target">{t('settings.transfer.targetLabel')}</Label>
              <Select value={selectedMembershipId} onValueChange={setSelectedMembershipId}>
                <SelectTrigger id="transfer-ownership-target" className="w-full">
                  <SelectValue placeholder={t('settings.transfer.targetPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {candidates.map((member) => (
                    <SelectItem key={member.id} value={member.id}>
                      {memberLabel(member)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <ConfirmActionDialog
              trigger={
                <Button variant="outline" disabled={!selectedMember}>
                  {t('settings.transfer.submit')}
                </Button>
              }
              title={t('settings.transfer.confirmTitle', { name: selectedMember ? memberLabel(selectedMember) : '' })}
              description={t('settings.transfer.confirmDescription')}
              confirmLabel={t('settings.transfer.submit')}
              onConfirm={confirmTransfer}
            />
          </div>
        )}
        {transferError && <ApiErrorMessage error={transferError} />}
      </CardContent>
    </Card>
  )
}
