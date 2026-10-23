import { describe, expect, it } from 'vitest'
import { buildListParams, parsePage } from './listParams'

describe('list params', () => {
  it('parses positive integer pages and falls back to 1', () => {
    expect(parsePage('3')).toBe(3)
    expect(parsePage(null)).toBe(1)
    expect(parsePage('0')).toBe(1)
    expect(parsePage('-2')).toBe(1)
    expect(parsePage('2.5')).toBe(1)
    expect(parsePage('abc')).toBe(1)
  })

  it('drops empty values and the first page', () => {
    expect(buildListParams({ search: '', page: 1, plan_id: undefined })).toEqual({})
    expect(buildListParams({ search: 'acme', page: 2, plan_id: 'pro' })).toEqual({
      search: 'acme',
      page: '2',
      plan_id: 'pro',
    })
  })
})
