import { describe, expect, it } from 'vitest'
import { BYTES_PER_MEGABYTE, bytesToMegabytes, formatCents, formatMegabytes, isPaidPlan } from '@/utils/billingFormat'

describe('billingFormat', () => {
  it('formats whole and fractional amounts', () => {
    expect(formatCents(1900, 'USD', 'en-US')).toBe('$19')
    expect(formatCents(1950, 'usd', 'en-US')).toBe('$19.50')
    expect(formatCents(19000, 'USD', 'en-US')).toBe('$190')
    expect(formatCents(999, 'EUR', 'en-US')).toBe('€9.99')
  })

  it('converts and formats megabytes', () => {
    expect(bytesToMegabytes(BYTES_PER_MEGABYTE * 3)).toBe(3)
    expect(formatMegabytes(0.25, 'en-US')).toBe('0.3')
    expect(formatMegabytes(5000, 'en-US')).toBe('5,000')
  })

  it('detects paid plans', () => {
    expect(isPaidPlan({ price_monthly_cents: 0, price_yearly_cents: 0 })).toBe(false)
    expect(isPaidPlan({ price_monthly_cents: 1900, price_yearly_cents: 19000 })).toBe(true)
  })
})
