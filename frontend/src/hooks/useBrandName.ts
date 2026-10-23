import { brand } from '@/config/brand'
import { usePublicConfig } from '@/contexts/PublicConfigContext'

export function useBrandName(): string {
  const publicConfig = usePublicConfig()
  return publicConfig.brand_name || brand.name
}
