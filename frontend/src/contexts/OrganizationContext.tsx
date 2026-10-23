import { createContext, useContext, useMemo, type ReactNode } from 'react'
import type { OrganizationSummary, OrgRole } from '@/types/api'
import { canPerform, type OrgAction } from '@/utils/orgPermissions'

export type { OrgAction } from '@/utils/orgPermissions'

interface OrganizationContextValue {
  organization: OrganizationSummary
  role: OrgRole
  can: (action: OrgAction) => boolean
}

const OrganizationContext = createContext<OrganizationContextValue | null>(null)

interface OrganizationProviderProps {
  organization: OrganizationSummary
  children: ReactNode
}

export function OrganizationProvider({ organization, children }: OrganizationProviderProps) {
  const contextValue = useMemo<OrganizationContextValue>(
    () => ({
      organization,
      role: organization.role,
      can: (action: OrgAction) => canPerform(organization.role, action),
    }),
    [organization],
  )
  return <OrganizationContext.Provider value={contextValue}>{children}</OrganizationContext.Provider>
}

export function useCurrentOrganization(): OrganizationContextValue {
  const contextValue = useContext(OrganizationContext)
  if (!contextValue) {
    throw new Error('useCurrentOrganization must be used inside OrganizationProvider')
  }
  return contextValue
}
