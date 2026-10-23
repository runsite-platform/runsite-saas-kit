import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { CopyLinkField } from '@/components/organizations/CopyLinkField'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { createInvitation } from '@/services/invitationService'
import type { InvitationCreated } from '@/types/api'
import { ApiError } from '@/utils/apiError'

const inviteSchema = z.object({
  email: z.string().trim().email('validation.emailInvalid'),
  role: z.enum(['admin', 'member']),
})

type InviteValues = z.infer<typeof inviteSchema>

interface InviteMemberDialogProps {
  memberLimit: number
  open: boolean
  onOpenChange: (open: boolean) => void
  onInvited: () => void
}

export function InviteMemberDialog({ memberLimit, open, onOpenChange, onInvited }: InviteMemberDialogProps) {
  const { t } = useTranslation('organizations')
  const { organization, can } = useCurrentOrganization()
  const [createdInvitation, setCreatedInvitation] = useState<InvitationCreated | null>(null)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: '', role: 'member' },
  })

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      reset()
      setCreatedInvitation(null)
      setSubmitError(null)
    }
    onOpenChange(nextOpen)
  }

  async function submitInvitation(values: InviteValues) {
    setSubmitError(null)
    try {
      const invitation = await createInvitation(organization.id, values)
      setCreatedInvitation(invitation)
      onInvited()
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error)
        return
      }
      throw error
    }
  }

  const isLimitReached = submitError?.code === 'plan_limit_reached'

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{createdInvitation ? t('invite.createdTitle') : t('invite.title')}</DialogTitle>
          <DialogDescription>
            {createdInvitation
              ? t('invite.createdDescription', { email: createdInvitation.invitation.email })
              : t('invite.description')}
          </DialogDescription>
        </DialogHeader>

        {createdInvitation ? (
          <div className="space-y-4">
            <CopyLinkField label={t('invite.linkLabel')} value={createdInvitation.invite_url} />
            <DialogFooter>
              <Button type="button" onClick={() => handleOpenChange(false)}>
                {t('invite.done')}
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit(submitInvitation)} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="invite-email">{t('invite.emailLabel')}</Label>
              <Input
                id="invite-email"
                type="email"
                autoComplete="off"
                autoFocus
                aria-invalid={Boolean(errors.email)}
                {...register('email')}
              />
              {errors.email?.message && <p className="text-sm text-destructive">{t(errors.email.message)}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-role">{t('invite.roleLabel')}</Label>
              <Controller
                control={control}
                name="role"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="invite-role" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">{t('roles.member')}</SelectItem>
                      <SelectItem value="admin">{t('roles.admin')}</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            {isLimitReached ? (
              <div
                role="alert"
                className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
              >
                <p>{t('invite.limitReached', { limit: memberLimit })}</p>
                {can('manage_billing') && (
                  <Link
                    to={`/app/${organization.slug}/billing`}
                    className="mt-1 inline-block font-medium underline underline-offset-4"
                    onClick={() => handleOpenChange(false)}
                  >
                    {t('invite.limitReachedAction')}
                  </Link>
                )}
              </div>
            ) : (
              submitError && <ApiErrorMessage error={submitError} />
            )}
            <DialogFooter>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? t('invite.submitting') : t('invite.submit')}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
