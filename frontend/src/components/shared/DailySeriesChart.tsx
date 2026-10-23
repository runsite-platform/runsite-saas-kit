import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DailyCount } from '@/types/api'
import { toDailyChartPoints } from '@/utils/statsFormatting'

interface DailySeriesChartProps {
  series: DailyCount[]
  seriesLabel: string
  kind?: 'bar' | 'line'
  height?: number
}

const AXIS_TICK = { fontSize: 12, fill: 'var(--muted-foreground)' }
const TOOLTIP_STYLE = {
  background: 'var(--popover)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  color: 'var(--popover-foreground)',
}
const CHART_MARGIN = { top: 8, right: 8, left: -16, bottom: 0 }

export function DailySeriesChart({ series, seriesLabel, kind = 'bar', height = 280 }: DailySeriesChartProps) {
  const { i18n } = useTranslation()
  const points = useMemo(() => toDailyChartPoints(series, i18n.language), [series, i18n.language])

  return (
    <ResponsiveContainer width="100%" height={height}>
      {kind === 'line' ? (
        <LineChart data={points} margin={CHART_MARGIN}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
          <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={false} minTickGap={16} />
          <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Line type="monotone" dataKey="count" name={seriesLabel} stroke="var(--chart-1)" strokeWidth={2} dot={false} />
        </LineChart>
      ) : (
        <BarChart data={points} margin={CHART_MARGIN}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
          <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={false} minTickGap={16} />
          <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'var(--muted)' }} />
          <Bar dataKey="count" name={seriesLabel} fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
        </BarChart>
      )}
    </ResponsiveContainer>
  )
}
