import { ArrowRightLeft, Bell, PartyPopper, ShieldCheck, UserMinus, UserPlus, type LucideIcon } from 'lucide-react'

interface NotificationKindStyle {
  icon: LucideIcon
  toneClassName: string
}

const NOTIFICATION_KIND_STYLES: Record<string, NotificationKindStyle> = {
  welcome: { icon: PartyPopper, toneClassName: 'bg-primary/10 text-primary' },
  member_joined: { icon: UserPlus, toneClassName: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
  member_role_changed: { icon: ShieldCheck, toneClassName: 'bg-sky-500/10 text-sky-600 dark:text-sky-400' },
  member_removed: { icon: UserMinus, toneClassName: 'bg-destructive/10 text-destructive' },
  ownership_transferred: { icon: ArrowRightLeft, toneClassName: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
}

const FALLBACK_KIND_STYLE: NotificationKindStyle = { icon: Bell, toneClassName: 'bg-muted text-muted-foreground' }

export function notificationKindStyle(kind: string): NotificationKindStyle {
  return NOTIFICATION_KIND_STYLES[kind] ?? FALLBACK_KIND_STYLE
}

const RELATIVE_TIME_STEPS: ReadonlyArray<[Intl.RelativeTimeFormatUnit, number]> = [
  ['second', 60],
  ['minute', 60],
  ['hour', 24],
  ['day', 7],
  ['week', 4.35],
  ['month', 12],
  ['year', Number.POSITIVE_INFINITY],
]

export function formatRelativeTime(isoDate: string, locale: string, now: number = Date.now()): string {
  let amount = (new Date(isoDate).getTime() - now) / 1000
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  for (const [unit, unitsInNextStep] of RELATIVE_TIME_STEPS) {
    if (Math.abs(amount) < unitsInNextStep) return formatter.format(Math.round(amount), unit)
    amount /= unitsInNextStep
  }
  return formatter.format(Math.round(amount), 'year')
}
