import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import type { BillingInterval } from '@/types/api'

const BILLING_INTERVALS: BillingInterval[] = ['monthly', 'yearly']

interface IntervalToggleProps {
  value: BillingInterval
  onChange: (interval: BillingInterval) => void
}

export function IntervalToggle({ value, onChange }: IntervalToggleProps) {
  const { t } = useTranslation('billing')
  return (
    <div role="group" aria-label={t('interval.label')} className="inline-flex gap-1 rounded-lg border bg-muted/40 p-1">
      {BILLING_INTERVALS.map((interval) => (
        <Button
          key={interval}
          type="button"
          size="sm"
          variant={value === interval ? 'default' : 'ghost'}
          aria-pressed={value === interval}
          onClick={() => onChange(interval)}
        >
          {t(`interval.${interval}`)}
        </Button>
      ))}
    </div>
  )
}
