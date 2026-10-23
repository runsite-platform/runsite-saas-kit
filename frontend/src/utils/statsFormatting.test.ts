import { describe, expect, it } from 'vitest'
import {
  formatRate,
  formatShortDate,
  formatStorageBytes,
  formatUsdCents,
  toDailyChartPoints,
  totalCount,
  usagePercent,
} from './statsFormatting'

describe('formatStorageBytes', () => {
  it('picks the largest unit below 1024', () => {
    expect(formatStorageBytes(0)).toBe('0 B')
    expect(formatStorageBytes(1536)).toBe('1.5 KB')
    expect(formatStorageBytes(100 * 1024 * 1024)).toBe('100 MB')
    expect(formatStorageBytes(5000 * 1024 * 1024)).toBe('4.9 GB')
  })

  it('stops at terabytes and treats negatives as zero', () => {
    expect(formatStorageBytes(2048 * 1024 ** 4)).toBe('2048 TB')
    expect(formatStorageBytes(-5)).toBe('0 B')
  })
})

describe('usagePercent', () => {
  it('rounds and clamps to 0..100', () => {
    expect(usagePercent(50, 200)).toBe(25)
    expect(usagePercent(300, 200)).toBe(100)
    expect(usagePercent(1, 0)).toBe(0)
  })
})

describe('money, rates and dates', () => {
  it('formats USD cents', () => {
    expect(formatUsdCents(3483, 'en-US')).toBe('$34.83')
  })

  it('formats rates and the empty rate', () => {
    expect(formatRate(0.5, 'en-US')).toBe('50%')
    expect(formatRate(0.6667, 'en-US')).toBe('66.7%')
    expect(formatRate(null, 'en-US')).toBe('—')
  })

  it('formats dates in UTC', () => {
    expect(formatShortDate('2026-03-01T23:30:00Z', 'en-US')).toBe('Mar 1, 2026')
  })
})

describe('daily series helpers', () => {
  const series = [
    { day: '2026-02-28', count: 1 },
    { day: '2026-03-01', count: 2 },
  ]

  it('adds UTC labels without shifting days', () => {
    expect(toDailyChartPoints(series, 'en-US')).toEqual([
      { day: '2026-02-28', label: 'Feb 28', count: 1 },
      { day: '2026-03-01', label: 'Mar 1', count: 2 },
    ])
  })

  it('sums counts', () => {
    expect(totalCount(series)).toBe(3)
    expect(totalCount([])).toBe(0)
  })
})
