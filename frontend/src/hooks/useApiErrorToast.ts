import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { classifyApiError } from '@/utils/classifyApiError'

export function useApiErrorToast(): (error: unknown) => void {
  const { t } = useTranslation('errors')
  const navigate = useNavigate()
  const { organization } = useCurrentOrganization()

  return useCallback(
    (error: unknown) => {
      const action = classifyApiError(error)
      if (action.kind === 'handled') {
        return
      }
      if (action.kind === 'plan_limit') {
        toast.error(t('plan_limit_reached'), {
          description: action.limit ? t(`plan_limit.${action.limit}`) : undefined,
          action: {
            label: t('upgrade_action'),
            onClick: () => navigate(`/app/${organization.slug}/billing`),
          },
        })
        return
      }
      toast.error(t(action.code, { defaultValue: action.message || t('unknown_error') }))
    },
    [navigate, organization.slug, t],
  )
}
