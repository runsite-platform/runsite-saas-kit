import { Link, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ThemeToggle } from '@/components/theme/ThemeToggle'
import { brand } from '@/config/brand'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { LogoMark } from '@/components/brand/LogoMark'

export function PublicLayout() {
  const { t } = useTranslation()
  const { brand_name: brandName } = usePublicConfig()

  return (
    <div className="flex min-h-svh flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <LogoMark className="size-7" />
            {brandName}
          </Link>
          <ThemeToggle />
        </div>
      </header>
      <main className="flex flex-1 flex-col">
        <Outlet />
      </main>
      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:justify-between">
          <span>{t('footer.copyright', { year: new Date().getFullYear(), brandName })}</span>
          <a href={brand.runsiteUrl} target="_blank" rel="noreferrer" className="hover:text-foreground">
            {t('footer.deployedOn')}
          </a>
        </div>
      </footer>
    </div>
  )
}
