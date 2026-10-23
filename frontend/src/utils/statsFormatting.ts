import type { DailyCount } from '@/types/api'

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB'] as const
const BYTES_PER_UNIT = 1024

export interface DailyChartPoint {
  day: string
  label: string
  count: number
}

export function formatStorageBytes(bytes: number): string {
  let value = Math.max(bytes, 0)
  let unitIndex = 0
  for (; unitIndex < BYTE_UNITS.length - 1 && value >= BYTES_PER_UNIT; unitIndex += 1) {
    value /= BYTES_PER_UNIT
  }
  const fractionDigits = unitIndex === 0 || value >= 10 ? 0 : 1
  return `${value.toFixed(fractionDigits)} ${BYTE_UNITS[unitIndex]}`
}

export function usagePercent(used: number, limit: number): number {
  if (limit <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((used / limit) * 100)))
}

export function formatUsdCents(cents: number, locale = 'en-US'): string {
  return new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD' }).format(cents / 100)
}

export function formatRate(rate: number | null, locale = 'en-US'): string {
  if (rate === null) return '—'
  return new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }).format(rate)
}

export function formatShortDate(isoDate: string, locale = 'en-US'): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(isoDate))
}

export function toDailyChartPoints(series: DailyCount[], locale = 'en-US'): DailyChartPoint[] {
  const labelFormatter = new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric', timeZone: 'UTC' })
  return series.map((point) => ({
    day: point.day,
    label: labelFormatter.format(new Date(`${point.day}T00:00:00Z`)),
    count: point.count,
  }))
}

export function totalCount(series: DailyCount[]): number {
  return series.reduce((sum, point) => sum + point.count, 0)
}
