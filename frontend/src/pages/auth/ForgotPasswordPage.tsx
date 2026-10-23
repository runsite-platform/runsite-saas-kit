import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { FormField } from '@/components/shared/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { authService } from '@/services/auth'
import { ApiError } from '@/utils/apiError'

const forgotPasswordSchema = z.object({
  email: z.string().trim().email('auth:validation.email_invalid'),
})

type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>

export function ForgotPasswordPage() {
  const { t } = useTranslation('auth')
  const [sent, setSent] = useState(false)
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(forgotPasswordSchema), defaultValues: { email: '' } })

  async function submit(values: ForgotPasswordValues) {
    setSubmitError(null)
    try {
      await authService.forgotPassword(values.email)
      setSent(true)
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
        <CardTitle>{t('forgot.title')}</CardTitle>
        <CardDescription>{t('forgot.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        {sent ? (
          <Alert>
            <AlertDescription>{t('forgot.sent')}</AlertDescription>
          </Alert>
        ) : (
          <form className="grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
            <FormField
              id="email"
              type="email"
              autoComplete="email"
              label={t('fields.email')}
              error={errors.email?.message ? t(errors.email.message) : undefined}
              {...register('email')}
            />
            {submitError ? <ApiErrorMessage error={submitError} /> : null}
            <Button type="submit" disabled={isSubmitting}>
              {t('forgot.submit')}
            </Button>
          </form>
        )}
      </CardContent>
      <CardFooter className="justify-center text-sm">
        <Link to="/login" className="underline-offset-4 hover:underline">
          {t('forgot.back_to_login')}
        </Link>
      </CardFooter>
    </Card>
  )
}
