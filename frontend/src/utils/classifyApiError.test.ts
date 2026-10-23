import { describe, expect, it } from 'vitest'
import { ApiError } from './apiError'
import { classifyApiError } from './classifyApiError'

function makeApiError(code: string, details: Record<string, unknown> = {}, message = 'Server message'): ApiError {
  return Object.assign(Object.create(ApiError.prototype) as ApiError, { code, details, message, status: 400 })
}

describe('classifyApiError', () => {
  it('turns plan_limit_reached into a plan limit action with the limit name', () => {
    expect(classifyApiError(makeApiError('plan_limit_reached', { limit: 'projects', plan_id: 'free' }))).toEqual({
      kind: 'plan_limit',
      limit: 'projects',
    })
  })

  it('treats plan_upgrade_required as already handled by fetchApi', () => {
    expect(classifyApiError(makeApiError('plan_upgrade_required'))).toEqual({ kind: 'handled' })
  })

  it('returns code and message for other API errors', () => {
    expect(classifyApiError(makeApiError('file_too_large'))).toEqual({
      kind: 'message',
      code: 'file_too_large',
      message: 'Server message',
    })
  })

  it('maps unknown errors to unknown_error', () => {
    expect(classifyApiError(new Error('boom'))).toEqual({ kind: 'message', code: 'unknown_error', message: 'boom' })
    expect(classifyApiError('text')).toEqual({ kind: 'message', code: 'unknown_error', message: '' })
  })
})
