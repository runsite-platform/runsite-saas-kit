import type { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  usagePercent?: number
}

const HIGH_USAGE_PERCENT = 90

export function StatCard({ title, value, hint, icon, usagePercent }: StatCardProps) {
  return (
    <Card className="gap-2">
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardDescription>{title}</CardDescription>
        {icon ? <span className="text-muted-foreground">{icon}</span> : null}
      </CardHeader>
      <CardContent className="space-y-2">
        <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
        {usagePercent !== undefined ? (
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label={title}
            aria-valuenow={usagePercent}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className={cn('h-full rounded-full', usagePercent >= HIGH_USAGE_PERCENT ? 'bg-destructive' : 'bg-primary')}
              style={{ width: `${usagePercent}%` }}
            />
          </div>
        ) : null}
        {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  )
}
