import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { z } from 'zod'
import { GoogleButton } from '@/components/auth/GoogleButton'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { FormField } from '@/components/shared/FormField'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { ApiError } from '@/utils/apiError'

const registerSchema = z.object({
  full_name: z.string().trim().max(200, 'auth:validation.full_name_max'),
  email: z.string().trim().email('auth:validation.email_invalid'),
  password: z.string().min(8, 'auth:validation.password_min').max(72, 'auth:validation.password_max'),
})

type RegisterValues = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { t } = useTranslation(['auth', 'errors'])
  const { register: registerAccount } = useAuth()
  const location = useLocation()
  const [submitError, setSubmitError] = useState<ApiError | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: '', email: '', password: '' },
  })

  async function submit(values: RegisterValues) {
    setSubmitError(null)
    try {
      await registerAccount(values)
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
        <CardTitle>{t('register.title')}</CardTitle>
        <CardDescription>{t('register.description')}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <GoogleButton />
        <form className="grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
          <FormField
            id="full_name"
            autoComplete="name"
            label={t('fields.full_name')}
            error={errors.full_name?.message ? t(errors.full_name.message) : undefined}
            {...register('full_name')}
          />
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
            autoComplete="new-password"
            label={t('fields.password')}
            error={errors.password?.message ? t(errors.password.message) : undefined}
            {...register('password')}
          />
          {submitError ? <ApiErrorMessage error={submitError} /> : null}
          <Button type="submit" disabled={isSubmitting}>
            {t('register.submit')}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="justify-center gap-1 text-sm text-muted-foreground">
        {t('register.have_account')}
        <Link to="/login" state={location.state} className="font-medium text-foreground underline-offset-4 hover:underline">
          {t('register.login_link')}
        </Link>
      </CardFooter>
    </Card>
  )
}
