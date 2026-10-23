import { useTranslation } from 'react-i18next'
import { Navigate } from 'react-router-dom'
import { DeleteOrganizationCard } from '@/components/organizations/DeleteOrganizationCard'
import { GeneralSettingsForm } from '@/components/organizations/GeneralSettingsForm'
import { LogoSection } from '@/components/organizations/LogoSection'
import { TransferOwnershipCard } from '@/components/organizations/TransferOwnershipCard'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'

export default function OrganizationSettingsPage() {
  const { t } = useTranslation('organizations')
  const { organization, can } = useCurrentOrganization()

  if (!can('manage_settings')) {
    return <Navigate to={`/app/${organization.slug}`} replace />
  }

  return (
    <div className="max-w-2xl space-y-8">
      <h1 className="text-2xl font-semibold">{t('settings.title')}</h1>
      <GeneralSettingsForm />
      <LogoSection />
      {can('delete_organization') && (
        <>
          <TransferOwnershipCard />
          <DeleteOrganizationCard />
        </>
      )}
    </div>
  )
}
