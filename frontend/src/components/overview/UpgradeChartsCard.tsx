import { Lock } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function UpgradeChartsCard({ organizationSlug }: { organizationSlug: string }) {
  const { t } = useTranslation('overview')
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lock className="size-4" aria-hidden="true" />
          {t('upgrade.title')}
        </CardTitle>
        <CardDescription>{t('upgrade.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild>
          <Link to={`/app/${organizationSlug}/billing`}>{t('upgrade.cta')}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
