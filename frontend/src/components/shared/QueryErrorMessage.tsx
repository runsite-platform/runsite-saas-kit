import { ApiErrorMessage } from '@/components/shared/ApiErrorMessage'

export function QueryErrorMessage({ error }: { error: unknown }) {
  return <ApiErrorMessage error={error} />
}
