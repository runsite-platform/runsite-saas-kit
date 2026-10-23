import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { AvatarSection } from '@/components/account/AvatarSection'
import { VerifyEmailBanner } from '@/components/auth/VerifyEmailBanner'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { LinkedAccountsSection } from '@/pages/account/LinkedAccountsSection'
import { PasswordSection } from '@/pages/account/PasswordSection'
import { ProfileSection } from '@/pages/account/ProfileSection'

export function AccountPage() {
  const { t } = useTranslation('account')
  const { user } = useAuth()
  if (!user) {
    return null
  }
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-10">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
        <Button asChild variant="ghost">
          <Link to="/app">{t('back_to_app')}</Link>
        </Button>
      </div>
      <VerifyEmailBanner />
      <AvatarSection />
      <ProfileSection user={user} />
      <PasswordSection key={user.has_password ? 'change-password' : 'set-password'} user={user} />
      <LinkedAccountsSection user={user} />
    </div>
  )
}
