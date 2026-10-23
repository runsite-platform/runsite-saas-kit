import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { PaymentRecord } from '@/types/api'
import { formatCents } from '@/utils/billingFormat'

interface PaymentHistoryTableProps {
  payments: PaymentRecord[]
}

export function PaymentHistoryTable({ payments }: PaymentHistoryTableProps) {
  const { t, i18n } = useTranslation('billing')
  if (payments.length === 0) {
    return <p className="text-sm text-muted-foreground">{t('payments.empty')}</p>
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t('payments.date')}</TableHead>
            <TableHead>{t('payments.amount')}</TableHead>
            <TableHead>{t('payments.status')}</TableHead>
            <TableHead className="text-right">{t('payments.invoice')}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {payments.map((payment) => (
            <TableRow key={payment.id}>
              <TableCell>
                {new Date(payment.paid_at ?? payment.created_at).toLocaleDateString(i18n.language, {
                  dateStyle: 'medium',
                })}
              </TableCell>
              <TableCell className="tabular-nums">
                {formatCents(payment.amount_cents, payment.currency, i18n.language)}
              </TableCell>
              <TableCell>
                <Badge variant={payment.status === 'failed' ? 'destructive' : 'secondary'}>
                  {t(`payments.statuses.${payment.status}`)}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                {payment.invoice_url ? (
                  <a
                    href={payment.invoice_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    {t('payments.view_invoice')}
                  </a>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
