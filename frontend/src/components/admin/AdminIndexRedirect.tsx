import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { isSuperadmin } from '@/utils/platformRoles'

export function AdminIndexRedirect() {
  const { user, impersonatedBy } = useAuth()
  return <Navigate to={isSuperadmin(user, impersonatedBy) ? '/admin/dashboard' : '/admin/users'} replace />
}
