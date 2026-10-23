import { ApiError } from './apiError'

export type ApiErrorAction =
  | { kind: 'plan_limit'; limit: string | null }
  | { kind: 'handled' }
  | { kind: 'message'; code: string; message: string }

export function classifyApiError(error: unknown): ApiErrorAction {
  if (!(error instanceof ApiError)) {
    return { kind: 'message', code: 'unknown_error', message: error instanceof Error ? error.message : '' }
  }
  if (error.code === 'plan_limit_reached') {
    const limit = typeof error.details.limit === 'string' ? error.details.limit : null
    return { kind: 'plan_limit', limit }
  }
  if (error.code === 'plan_upgrade_required') {
    return { kind: 'handled' }
  }
  return { kind: 'message', code: error.code, message: error.message }
}
