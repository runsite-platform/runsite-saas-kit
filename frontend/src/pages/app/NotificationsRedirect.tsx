import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { getLastOrganization } from '@/utils/returnPath'

export default function NotificationsRedirect() {
  const { organizations } = useAuth()
  if (organizations.length === 0) return <Navigate to="/app" replace />
  const lastOrganizationSlug = getLastOrganization()
  const targetOrganization =
    organizations.find((organization) => organization.slug === lastOrganizationSlug) ?? organizations[0]
  return <Navigate to={`/app/${targetOrganization.slug}/notifications`} replace />
}
