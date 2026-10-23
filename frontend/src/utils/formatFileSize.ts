const SIZE_UNITS = ['B', 'KB', 'MB', 'GB'] as const

export function formatFileSize(sizeBytes: number): string {
  let value = sizeBytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < SIZE_UNITS.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return unitIndex === 0 ? `${value} B` : `${value.toFixed(1)} ${SIZE_UNITS[unitIndex]}`
}
