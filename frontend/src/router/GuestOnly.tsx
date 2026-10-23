import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { PageLoader } from '@/components/shared/PageLoader'
import { useAuth } from '@/contexts/AuthContext'

function redirectTarget(state: unknown): string {
  if (state && typeof state === 'object' && 'from' in state && typeof state.from === 'string') {
    return state.from.startsWith('/') ? state.from : '/app'
  }
  return '/app'
}

export function GuestOnly() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') {
    return <PageLoader />
  }
  if (status === 'authenticated') {
    return <Navigate to={redirectTarget(location.state)} replace />
  }
  return <Outlet />
}
