import { UserRoundX } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { refreshAdminSession } from '@/services/adminService'
import { setAccessToken } from '@/utils/tokenStore'

export function ImpersonationBanner() {
  const { t } = useTranslation('admin')
  const { user, impersonatedBy, logout } = useAuth()
  const navigate = useNavigate()
  const [isStopping, setIsStopping] = useState(false)

  if (!impersonatedBy || !user) return null

  async function stopImpersonating() {
    setIsStopping(true)
    setAccessToken(null)
    try {
      const adminAccessToken = await refreshAdminSession()
      if (!adminAccessToken) {
        await logout().catch(() => undefined)
        setIsStopping(false)
        navigate('/login', { replace: true })
        return
      }
      window.location.assign('/admin/users')
    } catch {
      await logout().catch(() => undefined)
      setIsStopping(false)
      navigate('/login', { replace: true })
    }
  }

  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-center gap-3 bg-destructive px-4 py-2 text-sm text-white"
    >
      <span>{t('impersonation.banner', { email: user.email })}</span>
      <Button size="sm" variant="secondary" onClick={() => void stopImpersonating()} disabled={isStopping}>
        <UserRoundX className="size-4" aria-hidden="true" />
        {isStopping ? t('impersonation.stopping') : t('impersonation.stop')}
      </Button>
    </div>
  )
}
