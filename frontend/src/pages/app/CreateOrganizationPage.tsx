import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { CreateOrganizationForm } from '@/components/organizations/CreateOrganizationForm'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function CreateOrganizationPage() {
  const { t } = useTranslation('organizations')
  const navigate = useNavigate()

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/40 px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{t('create.title')}</CardTitle>
          <CardDescription>{t('create.pageDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          <CreateOrganizationForm onCreated={(organization) => navigate(`/app/${organization.slug}`)} />
        </CardContent>
      </Card>
    </div>
  )
}
