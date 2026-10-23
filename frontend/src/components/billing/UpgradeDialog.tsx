import { Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { onPlanUpgradeRequired, type PlanUpgradeDetails } from '@/utils/apiEvents'

export function UpgradeDialog() {
  const { t } = useTranslation('billing')
  const navigate = useNavigate()
  const { orgSlug } = useParams()
  const [details, setDetails] = useState<PlanUpgradeDetails | null>(null)

  useEffect(() => onPlanUpgradeRequired((nextDetails) => setDetails(nextDetails)), [])

  const close = () => setDetails(null)
  const viewPlans = () => {
    close()
    if (orgSlug) navigate(`/app/${orgSlug}/billing`)
  }

  const feature = details?.feature
  const requiredPlan = details?.required_plan ?? 'pro'
  const description = feature
    ? t('upgrade_dialog.description', {
        feature: t(`features.${feature}`, { defaultValue: feature }),
        plan: t(`plan_names.${requiredPlan}`, { defaultValue: requiredPlan }),
      })
    : t('upgrade_dialog.description_generic')

  return (
    <Dialog open={details !== null} onOpenChange={(open) => (open ? undefined : close())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-5 text-primary" aria-hidden />
            {t('upgrade_dialog.title')}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={close}>
            {t('upgrade_dialog.dismiss')}
          </Button>
          <Button onClick={viewPlans}>{t('upgrade_dialog.view_plans')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
