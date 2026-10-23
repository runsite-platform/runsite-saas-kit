import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation, useParams } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { OrganizationProvider } from '@/contexts/OrganizationContext'
import { rememberLastOrganization } from '@/utils/returnPath'

export function RequireOrganization() {
  const { orgSlug } = useParams()
  const location = useLocation()
  const { organizations } = useAuth()
  const organization = organizations.find((candidate) => candidate.slug === orgSlug)
  const [lastResolvedOrganizationId, setLastResolvedOrganizationId] = useState(organization?.id ?? null)
  if (organization && organization.id !== lastResolvedOrganizationId) {
    setLastResolvedOrganizationId(organization.id)
  }

  useEffect(() => {
    if (organization) {
      rememberLastOrganization(organization.slug)
    }
  }, [organization])

  if (!organization) {
    const renamedOrganization = organizations.find((candidate) => candidate.id === lastResolvedOrganizationId)
    if (renamedOrganization) {
      const pathInsideOrganization = location.pathname.slice(`/app/${orgSlug}`.length)
      return <Navigate to={`/app/${renamedOrganization.slug}${pathInsideOrganization}`} replace />
    }
    return <Navigate to="/app" replace />
  }
  return (
    <OrganizationProvider organization={organization}>
      <Outlet />
    </OrganizationProvider>
  )
}
