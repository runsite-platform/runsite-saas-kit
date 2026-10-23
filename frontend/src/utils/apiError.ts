export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function firstValidationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail) || detail.length === 0) return null
  const firstIssue: unknown = detail[0]
  return isRecord(firstIssue) && typeof firstIssue.msg === 'string' ? firstIssue.msg : null
}

export function apiErrorFromBody(status: number, body: unknown): ApiError {
  if (status === 422) {
    const detail = isRecord(body) ? body.detail : undefined
    return new ApiError(status, 'validation_error', firstValidationMessage(detail) ?? 'Validation failed', {
      errors: Array.isArray(detail) ? detail : [],
    })
  }
  const errorBody = isRecord(body) && isRecord(body.error) ? body.error : null
  if (errorBody && typeof errorBody.code === 'string') {
    const message = typeof errorBody.message === 'string' ? errorBody.message : errorBody.code
    const details = isRecord(errorBody.details) ? errorBody.details : {}
    return new ApiError(status, errorBody.code, message, details)
  }
  return new ApiError(status, 'unknown_error', `Request failed with status ${status}`)
}

export function networkError(cause: unknown): ApiError {
  const message = cause instanceof Error ? cause.message : 'Network request failed'
  return new ApiError(0, 'network_error', message)
}
