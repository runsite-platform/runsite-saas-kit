import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import '@/i18n'
import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'
import { ApiError } from '@/utils/apiError'

describe('ApiErrorMessage', () => {
  afterEach(() => cleanup())

  it('renders the translated message for a known code', () => {
    render(<ApiErrorMessage error={new ApiError(409, 'email_taken', 'Email already registered')} />)
    expect(screen.getByRole('alert').textContent).toBe('An account with this email already exists.')
  })

  it('falls back to the server message for an unknown code', () => {
    render(<ApiErrorMessage error={new ApiError(400, 'brand_new_code', 'Server says no')} />)
    expect(screen.getByRole('alert').textContent).toBe('Server says no')
  })

  it('renders the generic message for non-API errors', () => {
    render(<ApiErrorMessage error={new Error('boom')} />)
    expect(screen.getByRole('alert').textContent).toBe('Something went wrong. Please try again.')
  })

  it('renders nothing without an error', () => {
    const { container } = render(<ApiErrorMessage error={null} />)
    expect(container.innerHTML).toBe('')
  })
})
