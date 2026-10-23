import { Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export function PageLoader({ label }: { label?: string }) {
  const { t } = useTranslation('auth')
  return (
    <div role="status" className="flex min-h-[40vh] items-center justify-center gap-2 text-muted-foreground">
      <Loader2 className="size-5 animate-spin" aria-hidden="true" />
      <span>{label ?? t('loading')}</span>
    </div>
  )
}
