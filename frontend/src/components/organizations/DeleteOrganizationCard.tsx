import { useId, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { deleteOrganization } from '@/services/organizationService'
import { ApiError } from '@/utils/apiError'

export function DeleteOrganizationCard() {
  const { t } = useTranslation('organizations')
  const { organization } = useCurrentOrganization()
  const { reloadMe } = useAuth()
  const navigate = useNavigate()
  const confirmationInputId = useId()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [confirmationText, setConfirmationText] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<ApiError | null>(null)
  const isConfirmed = confirmationText.trim() === organization.slug

  function handleOpenChange(nextOpen: boolean) {
    setIsDialogOpen(nextOpen)
    if (!nextOpen) {
      setConfirmationText('')
      setDeleteError(null)
    }
  }

  async function deleteCurrentOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!isConfirmed) {
      return
    }
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await deleteOrganization(organization.id)
      await reloadMe()
      navigate('/app', { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setDeleteError(error)
        return
      }
      throw error
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Card className="border-destructive/50">
      <CardHeader>
        <CardTitle>{t('settings.delete.title')}</CardTitle>
        <CardDescription>{t('settings.delete.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Dialog open={isDialogOpen} onOpenChange={handleOpenChange}>
          <DialogTrigger asChild>
            <Button variant="destructive">{t('settings.delete.button')}</Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={(event) => void deleteCurrentOrganization(event)} className="space-y-4">
              <DialogHeader>
                <DialogTitle>{t('settings.delete.confirmTitle', { name: organization.name })}</DialogTitle>
                <DialogDescription>{t('settings.delete.confirmDescription')}</DialogDescription>
              </DialogHeader>
              <div className="space-y-2">
                <Label htmlFor={confirmationInputId}>
                  {t('settings.delete.confirmLabel', { slug: organization.slug })}
                </Label>
                <Input
                  id={confirmationInputId}
                  autoComplete="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={confirmationText}
                  onChange={(event) => setConfirmationText(event.target.value)}
                />
              </div>
              {deleteError && <ApiErrorMessage error={deleteError} />}
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                  {t('common.cancel')}
                </Button>
                <Button type="submit" variant="destructive" disabled={!isConfirmed || isDeleting}>
                  {isDeleting ? t('settings.delete.submitting') : t('settings.delete.submit')}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}
