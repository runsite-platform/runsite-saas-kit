import { describe, expect, it } from 'vitest'
import { formatRelativeTime, notificationKindStyle } from '@/components/notifications/notificationKinds'

const NOW = Date.parse('2026-10-23T12:00:00Z')

describe('formatRelativeTime', () => {
  it('formats recent and older dates in the largest fitting unit', () => {
    expect(formatRelativeTime('2026-10-23T11:59:30Z', 'en', NOW)).toBe('30 seconds ago')
    expect(formatRelativeTime('2026-10-23T09:00:00Z', 'en', NOW)).toBe('3 hours ago')
    expect(formatRelativeTime('2026-10-22T12:00:00Z', 'en', NOW)).toBe('yesterday')
    expect(formatRelativeTime('2024-10-23T12:00:00Z', 'en', NOW)).toBe('2 years ago')
  })
})

describe('notificationKindStyle', () => {
  it('falls back to a generic style for unknown kinds', () => {
    expect(notificationKindStyle('something_new')).toBe(notificationKindStyle('system'))
  })
})
