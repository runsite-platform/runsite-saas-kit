import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import CreateOrganizationPage from '@/pages/app/CreateOrganizationPage'
import { getLastOrganization, peekPendingInvitation } from '@/utils/returnPath'

export default function AppIndexPage() {
  const { organizations } = useAuth()

  const pendingInvitationPath = peekPendingInvitation()
  if (pendingInvitationPath) {
    return <Navigate to={pendingInvitationPath} replace />
  }
  if (organizations.length === 0) {
    return <CreateOrganizationPage />
  }
  const lastOrganizationSlug = getLastOrganization()
  const targetOrganization =
    organizations.find((organization) => organization.slug === lastOrganizationSlug) ?? organizations[0]
  return <Navigate to={`/app/${targetOrganization.slug}`} replace />
}
