import { Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'

interface CancelSubscriptionButtonProps {
  periodEnd: string | null
  isBusy: boolean
  disabled?: boolean
  onConfirm: () => void
}

export function CancelSubscriptionButton({ periodEnd, isBusy, disabled = false, onConfirm }: CancelSubscriptionButtonProps) {
  const { t, i18n } = useTranslation('billing')
  const description = periodEnd
    ? t('cancel.description', {
        date: new Date(periodEnd).toLocaleDateString(i18n.language, { dateStyle: 'medium' }),
      })
    : t('cancel.description_no_date')

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" disabled={disabled || isBusy}>
          {isBusy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
          {t('cancel.trigger')}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t('cancel.title')}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t('cancel.keep')}</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>{t('cancel.confirm')}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
