import type { PublicConfig } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export function fetchPublicConfig(signal?: AbortSignal): Promise<PublicConfig> {
  return fetchApi<PublicConfig>('/config/public', { auth: false, signal })
}
