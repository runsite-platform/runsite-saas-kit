import { ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { QueryErrorMessage } from '@/components/shared/QueryErrorMessage'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useApiQuery } from '@/hooks/useApiQuery'
import { cn } from '@/lib/utils'
import { getSetupChecklist } from '@/services/adminService'
import type { SetupChecklistStatus } from '@/types/api'

const STATUS_CLASS_NAMES: Record<SetupChecklistStatus, string> = {
  ok: 'border-transparent bg-emerald-600 text-white',
  missing: 'border-transparent bg-destructive text-white',
  warning: 'border-transparent bg-amber-500 text-black',
  manual: '',
}

export function AdminSetupPage() {
  const { t } = useTranslation('admin')
  const checklist = useApiQuery((signal) => getSetupChecklist(signal), [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t('setup.title')}</h1>
        <p className="text-sm text-muted-foreground">{t('setup.subtitle')}</p>
      </div>
      <QueryErrorMessage error={checklist.error} />
      {!checklist.data && checklist.isLoading ? (
        <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
      ) : null}
      {checklist.data ? (
        <Card className="py-0">
          <CardContent className="divide-y px-0">
            {checklist.data.items.map((item) => (
              <div key={item.id} className="flex flex-col gap-2 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <p className="font-medium">{t(`setup.items.${item.id}.title`)}</p>
                  <p className="text-sm text-muted-foreground">{t(`setup.items.${item.id}.description`)}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <Badge variant="outline" className={cn(STATUS_CLASS_NAMES[item.status])}>
                    {t(`setup.status.${item.status}`)}
                  </Badge>
                  <a
                    href={item.docs_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-sm underline underline-offset-4"
                  >
                    {t('setup.docs')}
                    <ExternalLink className="size-3" aria-hidden="true" />
                  </a>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
