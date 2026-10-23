import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { GoogleButton } from '@/components/auth/GoogleButton'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { FormField } from '@/components/shared/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { ApiError } from '@/utils/apiError'

const loginSchema = z.object({
  email: z.string().trim().email('auth:validation.email_invalid'),
  password: z.string().min(1, 'auth:validation.password_required'),
})

type LoginValues = z.infer<typeof loginSchema>

export function LoginPage() {
  const { t } = useTranslation(['auth', 'errors'])
  const { login } = useAuth()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const redirectErrorCode = searchParams.get('error')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(loginSchema), defaultValues: { email: '', password: '' } })

  async function submit(values: LoginValues) {
    setSubmitError(null)
    try {
      await login(values.email, values.password)
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
        <CardTitle>{t('login.title')}</CardTitle>
        <CardDescription>{t('login.description')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {redirectErrorCode ? (
          <Alert variant="destructive">
            <AlertDescription>
              {t(`errors:${redirectErrorCode}`, { defaultValue: t('errors:oauth_failed') })}
            </AlertDescription>
          </Alert>
        ) : null}
        <GoogleButton />
        <form className="grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
          <FormField
            id="email"
            type="email"
            autoComplete="email"
            label={t('fields.email')}
            error={errors.email?.message ? t(errors.email.message) : undefined}
            {...register('email')}
          />
          <FormField
            id="password"
            type="password"
            autoComplete="current-password"
            label={t('fields.password')}
            error={errors.password?.message ? t(errors.password.message) : undefined}
            {...register('password')}
          />
          <div className="flex justify-end text-sm">
            <Link to="/forgot-password" className="underline-offset-4 hover:underline">
              {t('login.forgot_password')}
            </Link>
          </div>
          {submitError ? <ApiErrorMessage error={submitError} /> : null}
          <Button type="submit" disabled={isSubmitting}>
            {t('login.submit')}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="justify-center gap-1 text-sm text-muted-foreground">
        {t('login.no_account')}
        <Link to="/register" state={location.state} className="font-medium text-foreground underline-offset-4 hover:underline">
          {t('login.register_link')}
        </Link>
      </CardFooter>
    </Card>
  )
}
