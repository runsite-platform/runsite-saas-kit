import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { brand } from '@/config/brand'
import { fetchPublicConfig } from '@/services/publicConfigService'
import type { PublicConfig } from '@/types/api'

const fallbackPublicConfig: PublicConfig = {
  brand_name: brand.name,
  features: { google_login: false, billing: false, file_uploads: false, email: false },
}

const PublicConfigContext = createContext<PublicConfig | null>(null)

export function PublicConfigProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const [config, setConfig] = useState<PublicConfig | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchPublicConfig(controller.signal)
      .then(setConfig)
      .catch(() => {
        if (!controller.signal.aborted) setConfig(fallbackPublicConfig)
      })
    return () => controller.abort()
  }, [])

  if (!config) {
    return (
      <div className="flex min-h-svh items-center justify-center text-sm text-muted-foreground">{t('loading')}</div>
    )
  }

  return <PublicConfigContext.Provider value={config}>{children}</PublicConfigContext.Provider>
}

export function usePublicConfig(): PublicConfig {
  const config = useContext(PublicConfigContext)
  if (!config) throw new Error('usePublicConfig must be used inside PublicConfigProvider')
  return config
}
