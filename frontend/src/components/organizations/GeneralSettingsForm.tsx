import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { updateOrganization } from '@/services/organizationService'
import { ApiError } from '@/utils/apiError'

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

const generalSettingsSchema = z.object({
  name: z.string().trim().min(1, 'validation.nameRequired').max(120, 'validation.nameTooLong'),
  slug: z
    .string()
    .trim()
    .toLowerCase()
    .max(64, 'validation.slugInvalid')
    .regex(SLUG_PATTERN, 'validation.slugInvalid'),
})

type GeneralSettingsValues = z.infer<typeof generalSettingsSchema>

export function GeneralSettingsForm() {
  const { t } = useTranslation('organizations')
  const { organization } = useCurrentOrganization()
  const { reloadMe } = useAuth()
  const navigate = useNavigate()
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const [isSaved, setIsSaved] = useState(false)
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<GeneralSettingsValues>({
    resolver: zodResolver(generalSettingsSchema),
    defaultValues: { name: organization.name, slug: organization.slug },
  })
  const slugValue = useWatch({ control, name: 'slug' })

  useEffect(() => {
    reset({ name: organization.name, slug: organization.slug })
  }, [organization.name, organization.slug, reset])

  async function saveSettings(values: GeneralSettingsValues) {
    setSubmitError(null)
    setIsSaved(false)
    try {
      const updatedOrganization = await updateOrganization(organization.id, values)
      await reloadMe()
      setIsSaved(true)
      if (updatedOrganization.slug !== organization.slug) {
        navigate(`/app/${updatedOrganization.slug}/settings`, { replace: true })
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error)
        return
      }
      throw error
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.general.title')}</CardTitle>
        <CardDescription>{t('settings.general.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(saveSettings)} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="organization-settings-name">{t('settings.general.nameLabel')}</Label>
            <Input id="organization-settings-name" aria-invalid={Boolean(errors.name)} {...register('name')} />
            {errors.name?.message && <p className="text-sm text-destructive">{t(errors.name.message)}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="organization-settings-slug">{t('settings.general.slugLabel')}</Label>
            <Input
              id="organization-settings-slug"
              autoCapitalize="none"
              spellCheck={false}
              aria-invalid={Boolean(errors.slug)}
              aria-describedby="organization-settings-slug-hint"
              {...register('slug')}
            />
            <p id="organization-settings-slug-hint" className="text-xs text-muted-foreground">
              {t('settings.general.slugHint', { slug: slugValue })}
            </p>
            {errors.slug?.message && <p className="text-sm text-destructive">{t(errors.slug.message)}</p>}
          </div>
          {submitError && <ApiErrorMessage error={submitError} />}
          {isSaved && (
            <p role="status" className="text-sm text-muted-foreground">
              {t('settings.general.saved')}
            </p>
          )}
          <Button type="submit" disabled={isSubmitting || !isDirty}>
            {isSubmitting ? t('settings.general.saving') : t('settings.general.save')}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
