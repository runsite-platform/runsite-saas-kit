// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { ApiError, apiErrorFromBody, networkError } from '@/utils/apiError'

describe('apiErrorFromBody', () => {
  it('reads code, message and details from the error envelope', () => {
    const error = apiErrorFromBody(402, {
      error: { code: 'plan_limit_reached', message: 'Limit reached', details: { limit: 'projects' } },
    })
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(402)
    expect(error.code).toBe('plan_limit_reached')
    expect(error.message).toBe('Limit reached')
    expect(error.details).toEqual({ limit: 'projects' })
  })

  it('defaults details to an empty object', () => {
    const error = apiErrorFromBody(409, { error: { code: 'email_taken', message: 'Email taken' } })
    expect(error.details).toEqual({})
  })

  it('maps FastAPI validation errors to validation_error', () => {
    const detail = [{ loc: ['body', 'email'], msg: 'value is not a valid email address', type: 'value_error' }]
    const error = apiErrorFromBody(422, { detail })
    expect(error.code).toBe('validation_error')
    expect(error.message).toBe('value is not a valid email address')
    expect(error.details).toEqual({ errors: detail })
  })

  it('falls back to unknown_error for unexpected bodies', () => {
    const error = apiErrorFromBody(500, 'Internal Server Error')
    expect(error.code).toBe('unknown_error')
    expect(error.message).toBe('Request failed with status 500')
  })
})

describe('networkError', () => {
  it('uses status 0 and network_error code', () => {
    const error = networkError(new TypeError('Failed to fetch'))
    expect(error.status).toBe(0)
    expect(error.code).toBe('network_error')
    expect(error.message).toBe('Failed to fetch')
  })
})
