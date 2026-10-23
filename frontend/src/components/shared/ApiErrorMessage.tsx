import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { ApiError } from '@/utils/apiError'

interface ApiErrorMessageProps {
  error: unknown
  className?: string
}

export function ApiErrorMessage({ error, className }: ApiErrorMessageProps) {
  const { t } = useTranslation('errors')
  if (!error) return null

  const code = error instanceof ApiError ? error.code : 'unknown_error'
  const fallback = error instanceof ApiError ? error.message : t('unknown_error')

  return (
    <p role="alert" className={cn('text-sm text-destructive', className)}>
      {t(code, { defaultValue: fallback })}
    </p>
  )
}
