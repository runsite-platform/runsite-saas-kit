export function parsePage(value: string | null): number {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed >= 1 ? parsed : 1
}

export function buildListParams(values: Record<string, string | number | undefined>): Record<string, string> {
  const params: Record<string, string> = {}
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === '') continue
    if (key === 'page' && Number(value) <= 1) continue
    params[key] = String(value)
  }
  return params
}
