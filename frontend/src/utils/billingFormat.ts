export const BYTES_PER_MEGABYTE = 1024 * 1024

export function formatCents(amountCents: number, currency = 'USD', locale?: string): string {
  const hasFraction = amountCents % 100 !== 0
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency.toUpperCase(),
    minimumFractionDigits: hasFraction ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(amountCents / 100)
}

export function bytesToMegabytes(bytes: number): number {
  return bytes / BYTES_PER_MEGABYTE
}

export function formatMegabytes(megabytes: number, locale?: string): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: megabytes < 10 ? 1 : 0 }).format(megabytes)
}

export function isPaidPlan(plan: { price_monthly_cents: number; price_yearly_cents: number }): boolean {
  return plan.price_monthly_cents > 0 || plan.price_yearly_cents > 0
}
