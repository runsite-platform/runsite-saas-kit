import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { ImpersonationBanner } from '@/components/admin/ImpersonationBanner'
import { PageLoader } from '@/components/shared/PageLoader'
import { useAuth } from '@/contexts/AuthContext'

export function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') {
    return <PageLoader />
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />
  }
  return (
    <>
      <ImpersonationBanner />
      <Outlet />
    </>
  )
}
