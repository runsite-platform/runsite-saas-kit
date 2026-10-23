import { cn } from '@/lib/utils'

export const LOGO_LETTER_PATH =
  'M20.6 11.6C19.7 10.3 18.1 9.5 16 9.5c-2.8 0-4.5 1.4-4.5 3.4 0 2.1 1.9 2.8 4.5 3.3 2.8.5 4.6 1.3 4.6 3.4 0 2.1-1.9 3.2-4.6 3.2-2.2 0-3.9-.8-4.8-2.2'

interface LogoMarkProps {
  className?: string
}

export function LogoMark({ className }: LogoMarkProps) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn('size-8 shrink-0', className)}>
      <rect width="32" height="32" rx="8" className="fill-primary" />
      <path
        d={LOGO_LETTER_PATH}
        fill="none"
        strokeWidth="3.2"
        strokeLinecap="round"
        className="stroke-primary-foreground"
      />
    </svg>
  )
}
