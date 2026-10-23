import { describe, expect, it } from 'vitest'
import { formatFileSize } from './formatFileSize'

describe('formatFileSize', () => {
  it('formats bytes, kilobytes, megabytes and gigabytes', () => {
    expect(formatFileSize(0)).toBe('0 B')
    expect(formatFileSize(512)).toBe('512 B')
    expect(formatFileSize(1536)).toBe('1.5 KB')
    expect(formatFileSize(25 * 1024 * 1024)).toBe('25.0 MB')
    expect(formatFileSize(3 * 1024 * 1024 * 1024)).toBe('3.0 GB')
  })

  it('keeps gigabytes as the largest unit', () => {
    expect(formatFileSize(2048 * 1024 * 1024 * 1024)).toBe('2048.0 GB')
  })
})
