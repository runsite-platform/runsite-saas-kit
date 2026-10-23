import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ThemeToggle } from '@/components/theme/ThemeToggle'
import { Button } from '@/components/ui/button'
import { useBrandName } from '@/hooks/useBrandName'
import { LogoMark } from '@/components/brand/LogoMark'

export function LandingHeader() {
  const { t } = useTranslation('landing')
  const brandName = useBrandName()

  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Link to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight text-foreground">
          <LogoMark />
          <span>{brandName}</span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm font-medium text-muted-foreground md:flex">
          <a href="#features" className="hover:text-foreground">
            {t('landing:nav.features')}
          </a>
          <a href="#how-it-works" className="hover:text-foreground">
            {t('landing:nav.howItWorks')}
          </a>
          <a href="#pricing" className="hover:text-foreground">
            {t('landing:nav.pricing')}
          </a>
          <a href="#faq" className="hover:text-foreground">
            {t('landing:nav.faq')}
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm">
            <Link to="/login">{t('landing:nav.login')}</Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/register">{t('landing:nav.register')}</Link>
          </Button>
        </div>
      </div>
    </header>
  )
}
