import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import type { ChartRangeDays } from '@/types/api'

const RANGE_OPTIONS: readonly ChartRangeDays[] = [30, 90]

interface RangeToggleProps {
  value: ChartRangeDays
  onChange: (days: ChartRangeDays) => void
}

export function RangeToggle({ value, onChange }: RangeToggleProps) {
  const { t } = useTranslation('overview')
  return (
    <div className="inline-flex rounded-md border p-0.5" role="group" aria-label={t('range.label')}>
      {RANGE_OPTIONS.map((days) => (
        <Button
          key={days}
          type="button"
          size="sm"
          variant={days === value ? 'secondary' : 'ghost'}
          aria-pressed={days === value}
          onClick={() => onChange(days)}
        >
          {t('range.last_days', { count: days })}
        </Button>
      ))}
    </div>
  )
}
