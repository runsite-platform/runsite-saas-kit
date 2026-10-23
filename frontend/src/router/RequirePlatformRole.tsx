import type { ReactNode } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { hasPlatformRole } from '@/utils/platformRoles'

interface RequirePlatformRoleProps {
  roles: readonly string[]
  children?: ReactNode
}

export function RequirePlatformRole({ roles, children }: RequirePlatformRoleProps) {
  const { status, user, impersonatedBy } = useAuth()
  if (status === 'loading') return null
  if (!hasPlatformRole(user, impersonatedBy, roles)) return <Navigate to="/app" replace />
  return children ? <>{children}</> : <Outlet />
}
