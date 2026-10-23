import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { RunsiteCredit } from '@/components/landing/RunsiteCredit'
import { brand } from '@/config/brand'
import { useBrandName } from '@/hooks/useBrandName'

export function LandingFooter() {
  const { t } = useTranslation('landing')
  const brandName = useBrandName()
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-muted-foreground md:flex-row">
        <p>{t('landing:footer.copyright', { year: currentYear, brandName })}</p>
        <nav className="flex items-center gap-6">
          <Link to="/pricing" className="hover:text-foreground">
            {t('landing:footer.pricing')}
          </Link>
          <Link to="/login" className="hover:text-foreground">
            {t('landing:footer.login')}
          </Link>
          <a href={`mailto:${brand.supportEmail}`} className="hover:text-foreground">
            {t('landing:footer.contact')}
          </a>
        </nav>
        <RunsiteCredit />
      </div>
    </footer>
  )
}
