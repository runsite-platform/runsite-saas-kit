import { CreditCard } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const PROVIDER_VARIABLES = [
  {
    provider: 'stripe',
    variables: [
      'BILLING_PROVIDER=stripe',
      'STRIPE_SECRET_KEY',
      'STRIPE_WEBHOOK_SECRET',
      'STRIPE_PRICE_PRO_MONTHLY',
      'STRIPE_PRICE_PRO_YEARLY',
    ],
  },
  {
    provider: 'lemonsqueezy',
    variables: [
      'BILLING_PROVIDER=lemonsqueezy',
      'LEMONSQUEEZY_API_KEY',
      'LEMONSQUEEZY_STORE_ID',
      'LEMONSQUEEZY_WEBHOOK_SECRET',
      'LEMONSQUEEZY_VARIANT_PRO_MONTHLY',
      'LEMONSQUEEZY_VARIANT_PRO_YEARLY',
    ],
  },
  {
    provider: 'creem',
    variables: [
      'BILLING_PROVIDER=creem',
      'CREEM_API_KEY',
      'CREEM_API_URL',
      'CREEM_WEBHOOK_SECRET',
      'CREEM_PRODUCT_PRO_MONTHLY',
      'CREEM_PRODUCT_PRO_YEARLY',
    ],
  },
] as const

export function BillingDisabledNotice() {
  const { t } = useTranslation('billing')
  const origin = window.location.origin

  return (
    <Alert>
      <CreditCard className="size-4" aria-hidden />
      <AlertTitle>{t('disabled.title')}</AlertTitle>
      <AlertDescription className="space-y-4">
        <p>{t('disabled.description')}</p>
        <div className="grid gap-4 md:grid-cols-3">
          {PROVIDER_VARIABLES.map(({ provider, variables }) => (
            <section key={provider} className="min-w-0 space-y-2 rounded-md border p-3">
              <h3 className="font-medium text-foreground">{t(`disabled.providers.${provider}`)}</h3>
              <p className="text-xs">{t('disabled.variables')}</p>
              <ul className="space-y-1">
                {variables.map((variable) => (
                  <li key={variable}>
                    <code className="break-all rounded bg-muted px-1 py-0.5 text-xs">{variable}</code>
                  </li>
                ))}
              </ul>
              <p className="text-xs">{t('disabled.webhook')}</p>
              <code className="block break-all rounded bg-muted px-1 py-0.5 text-xs">
                {`${origin}/api/webhooks/billing/${provider}`}
              </code>
            </section>
          ))}
        </div>
      </AlertDescription>
    </Alert>
  )
}
