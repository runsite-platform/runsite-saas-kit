import { useState, type MouseEvent, type ReactNode } from 'react'
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

interface ConfirmActionDialogProps {
  trigger: ReactNode
  title: string
  description: string
  confirmLabel: string
  onConfirm: () => Promise<void>
}

export function ConfirmActionDialog({ trigger, title, description, confirmLabel, onConfirm }: ConfirmActionDialogProps) {
  const { t } = useTranslation('organizations')
  const [isOpen, setIsOpen] = useState(false)
  const [isWorking, setIsWorking] = useState(false)

  async function confirmAction(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault()
    setIsWorking(true)
    try {
      await onConfirm()
      setIsOpen(false)
    } finally {
      setIsWorking(false)
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isWorking}>{t('common.cancel')}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isWorking} onClick={(event) => void confirmAction(event)}>
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
