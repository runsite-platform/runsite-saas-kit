import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { ImageUploadField } from '@/components/shared/ImageUploadField'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { removeLogo, uploadLogo } from '@/services/organizationService'

export function LogoSection() {
  const { t } = useTranslation('organizations')
  const { organization, can } = useCurrentOrganization()
  const { reloadMe } = useAuth()
  const { features } = usePublicConfig()

  if (!features.file_uploads || !can('manage_settings')) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('logo.title')}</CardTitle>
        <CardDescription>{t('logo.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ImageUploadField
          imageUrl={organization.logo_url}
          fallbackText={organization.name.slice(0, 2).toUpperCase()}
          onUpload={async (file) => {
            await uploadLogo(organization.id, file)
            await reloadMe()
            toast.success(t('logo.updated'))
          }}
          onRemove={async () => {
            await removeLogo(organization.id)
            await reloadMe()
            toast.success(t('logo.removed'))
          }}
        />
      </CardContent>
    </Card>
  )
}
