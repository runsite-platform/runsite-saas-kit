import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo, useState } from 'react'
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

function buildPasswordSchema(requiresCurrentPassword: boolean) {
  return z
    .object({
      current_password: z.string(),
      new_password: z.string().min(8, 'account:validation.password_min').max(72, 'account:validation.password_max'),
      confirm_password: z.string(),
    })
    .superRefine((values, context) => {
      if (requiresCurrentPassword && values.current_password.length === 0) {
        context.addIssue({
          code: 'custom',
          path: ['current_password'],
          message: 'account:validation.current_required',
        })
      }
      if (values.new_password !== values.confirm_password) {
        context.addIssue({
          code: 'custom',
          path: ['confirm_password'],
          message: 'account:validation.passwords_mismatch',
        })
      }
    })
}

type PasswordValues = z.infer<ReturnType<typeof buildPasswordSchema>>

export function PasswordSection({ user }: { user: User }) {
  const { t } = useTranslation('account')
  const { reloadMe } = useAuth()
  const requiresCurrentPassword = user.has_password
  const passwordSchema = useMemo(() => buildPasswordSchema(requiresCurrentPassword), [requiresCurrentPassword])
  const [saved, setSaved] = useState(false)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: '', new_password: '', confirm_password: '' },
  })

  async function submit(values: PasswordValues) {
    setSaved(false)
    setSubmitError(null)
    try {
      await meService.changePassword({
        current_password: requiresCurrentPassword ? values.current_password : null,
        new_password: values.new_password,
      })
      reset()
      setSaved(true)
      if (!requiresCurrentPassword) {
        await reloadMe()
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
        <CardTitle>{t('password.title')}</CardTitle>
        <CardDescription>
          {requiresCurrentPassword ? t('password.description_change') : t('password.description_set')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
          {requiresCurrentPassword ? (
            <FormField
              id="current_password"
              type="password"
              autoComplete="current-password"
              label={t('password.current')}
              error={errors.current_password?.message ? t(errors.current_password.message) : undefined}
              {...register('current_password')}
            />
          ) : null}
          <FormField
            id="new_password"
            type="password"
            autoComplete="new-password"
            label={t('password.new')}
            error={errors.new_password?.message ? t(errors.new_password.message) : undefined}
            {...register('new_password')}
          />
          <FormField
            id="confirm_new_password"
            type="password"
            autoComplete="new-password"
            label={t('password.confirm')}
            error={errors.confirm_password?.message ? t(errors.confirm_password.message) : undefined}
            {...register('confirm_password')}
          />
          {submitError ? <ApiErrorMessage error={submitError} /> : null}
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={isSubmitting}>
              {t('password.save')}
            </Button>
            {saved ? (
              <span role="status" className="text-sm text-muted-foreground">
                {t('password.saved')}
              </span>
            ) : null}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
