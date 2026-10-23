import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { FormField } from '@/components/shared/FormField'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { meService } from '@/services/me'
import type { User } from '@/types/api'
import { ApiError } from '@/utils/apiError'

const profileSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, 'account:validation.full_name_required')
    .max(200, 'account:validation.full_name_max'),
})

type ProfileValues = z.infer<typeof profileSchema>

export function ProfileSection({ user }: { user: User }) {
  const { t } = useTranslation('account')
  const { reloadMe } = useAuth()
  const [saved, setSaved] = useState(false)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(profileSchema), defaultValues: { full_name: user.full_name } })

  async function submit(values: ProfileValues) {
    setSaved(false)
    setSubmitError(null)
    try {
      await meService.updateProfile(values.full_name)
      await reloadMe()
      setSaved(true)
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
        <CardTitle>{t('profile.title')}</CardTitle>
        <CardDescription>{t('profile.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
          <FormField id="account-email" label={t('profile.email')} value={user.email} readOnly disabled />
          <FormField
            id="full_name"
            autoComplete="name"
            label={t('profile.full_name')}
            error={errors.full_name?.message ? t(errors.full_name.message) : undefined}
            {...register('full_name')}
          />
          {submitError ? <ApiErrorMessage error={submitError} /> : null}
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={isSubmitting}>
              {t('profile.save')}
            </Button>
            {saved ? (
              <span role="status" className="text-sm text-muted-foreground">
                {t('profile.saved')}
              </span>
            ) : null}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
