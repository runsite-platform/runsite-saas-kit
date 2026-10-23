import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { NativeSelect } from '@/components/admin/NativeSelect'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { overridePlan } from '@/services/adminService'
import type { AdminOrganizationDetail, PlanInfo } from '@/types/api'

const planOverrideSchema = z.object({
  plan_id: z.string(),
  reason: z.string().trim().min(3).max(500),
})

type PlanOverrideValues = z.infer<typeof planOverrideSchema>

interface PlanOverrideFormProps {
  organization: AdminOrganizationDetail
  plans: PlanInfo[]
  onSaved: () => void
}

export function PlanOverrideForm({ organization, plans, onSaved }: PlanOverrideFormProps) {
  const { t } = useTranslation('admin')
  const [submitError, setSubmitError] = useState<unknown>(null)
  const [isSaved, setIsSaved] = useState(false)
  const form = useForm<PlanOverrideValues>({
    resolver: zodResolver(planOverrideSchema),
    defaultValues: { plan_id: organization.plan_override_id ?? '', reason: '' },
  })

  async function submit(values: PlanOverrideValues) {
    setSubmitError(null)
    setIsSaved(false)
    try {
      await overridePlan(organization.id, { plan_id: values.plan_id || null, reason: values.reason })
      setIsSaved(true)
      form.reset({ plan_id: values.plan_id, reason: '' })
      onSaved()
    } catch (error) {
      setSubmitError(error)
    }
  }

  return (
    <form onSubmit={form.handleSubmit(submit)} className="space-y-4" noValidate>
      {organization.plan_override_reason ? (
        <p className="text-sm text-muted-foreground">
          {t('organizations.override.current_reason', { reason: organization.plan_override_reason })}
        </p>
      ) : null}
      <div className="space-y-2">
        <Label htmlFor="plan-override-plan">{t('organizations.override.plan')}</Label>
        <NativeSelect id="plan-override-plan" className="w-full" {...form.register('plan_id')}>
          <option value="">{t('organizations.override.no_override')}</option>
          {plans.map((plan) => (
            <option key={plan.id} value={plan.id}>
              {t(`plans.${plan.id}`, { defaultValue: plan.name })}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="space-y-2">
        <Label htmlFor="plan-override-reason">{t('organizations.override.reason')}</Label>
        <Textarea
          id="plan-override-reason"
          rows={3}
          maxLength={500}
          aria-invalid={Boolean(form.formState.errors.reason)}
          aria-describedby={form.formState.errors.reason ? 'plan-override-reason-error' : undefined}
          {...form.register('reason')}
        />
        {form.formState.errors.reason ? (
          <p id="plan-override-reason-error" className="text-sm text-destructive">
            {t('organizations.override.reason_invalid')}
          </p>
        ) : null}
      </div>
      <QueryErrorMessage error={submitError} />
      {isSaved ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t('organizations.override.saved')}
        </p>
      ) : null}
      <Button type="submit" disabled={form.formState.isSubmitting}>
        {t('organizations.override.submit')}
      </Button>
    </form>
  )
}
