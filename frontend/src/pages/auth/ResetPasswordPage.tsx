import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { FormField } from '@/components/shared/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { authService } from '@/services/auth'
import { ApiError } from '@/utils/apiError'

const resetPasswordSchema = z
  .object({
    password: z.string().min(8, 'auth:validation.password_min').max(72, 'auth:validation.password_max'),
    confirm_password: z.string(),
  })
  .refine((values) => values.password === values.confirm_password, {
    path: ['confirm_password'],
    message: 'auth:validation.passwords_mismatch',
  })

type ResetPasswordValues = z.infer<typeof resetPasswordSchema>

export function ResetPasswordPage() {
  const { t } = useTranslation('auth')
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [completed, setCompleted] = useState(false)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirm_password: '' },
  })

  async function submit(values: ResetPasswordValues) {
    if (!token) {
      return
    }
    setSubmitError(null)
    try {
      await authService.resetPassword(token, values.password)
      setCompleted(true)
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
        <CardTitle>{t('reset.title')}</CardTitle>
        <CardDescription>{t('reset.description')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {!token ? (
          <Alert variant="destructive">
            <AlertDescription className="grid gap-2">
              <span>{t('reset.missing_token')}</span>
              <Link to="/forgot-password" className="font-medium underline-offset-4 hover:underline">
                {t('reset.request_new')}
              </Link>
            </AlertDescription>
          </Alert>
        ) : completed ? (
          <Alert>
            <AlertDescription className="grid gap-2">
              <span>{t('reset.success')}</span>
              <Link to="/login" className="font-medium underline-offset-4 hover:underline">
                {t('reset.login_link')}
              </Link>
            </AlertDescription>
          </Alert>
        ) : (
          <form className="grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
            <FormField
              id="password"
              type="password"
              autoComplete="new-password"
              label={t('fields.new_password')}
              error={errors.password?.message ? t(errors.password.message) : undefined}
              {...register('password')}
            />
            <FormField
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              label={t('fields.confirm_password')}
              error={errors.confirm_password?.message ? t(errors.confirm_password.message) : undefined}
              {...register('confirm_password')}
            />
            {submitError ? <ApiErrorMessage error={submitError} /> : null}
            <Button type="submit" disabled={isSubmitting}>
              {t('reset.submit')}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
