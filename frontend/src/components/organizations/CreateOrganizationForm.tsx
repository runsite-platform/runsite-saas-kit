import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/contexts/AuthContext'
import { createOrganization } from '@/services/organizationService'
import type { OrganizationSummary } from '@/types/api'
import { ApiError } from '@/utils/apiError'

const createOrganizationSchema = z.object({
  name: z.string().trim().min(1, 'validation.nameRequired').max(120, 'validation.nameTooLong'),
})

type CreateOrganizationValues = z.infer<typeof createOrganizationSchema>

interface CreateOrganizationFormProps {
  onCreated: (organization: OrganizationSummary) => void
}

export function CreateOrganizationForm({ onCreated }: CreateOrganizationFormProps) {
  const { t } = useTranslation('organizations')
  const { reloadMe } = useAuth()
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateOrganizationValues>({
    resolver: zodResolver(createOrganizationSchema),
    defaultValues: { name: '' },
  })

  async function submitOrganization(values: CreateOrganizationValues) {
    setSubmitError(null)
    try {
      const organization = await createOrganization(values.name)
      await reloadMe()
      onCreated(organization)
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error)
        return
      }
      throw error
    }
  }

  return (
    <form onSubmit={handleSubmit(submitOrganization)} className="space-y-4" noValidate>
      <div className="space-y-2">
        <Label htmlFor="organization-name">{t('create.nameLabel')}</Label>
        <Input
          id="organization-name"
          autoFocus
          autoComplete="organization"
          placeholder={t('create.namePlaceholder')}
          aria-invalid={Boolean(errors.name)}
          {...register('name')}
        />
        {errors.name?.message && <p className="text-sm text-destructive">{t(errors.name.message)}</p>}
      </div>
      {submitError && <ApiErrorMessage error={submitError} />}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? t('create.submitting') : t('create.submit')}
      </Button>
    </form>
  )
}
