import { ArrowLeft, Building2, LayoutDashboard, ListChecks, Shield, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { cn } from '@/lib/utils'
import { isSuperadmin } from '@/utils/platformRoles'

export function AdminLayout() {
  const { t } = useTranslation('admin')
  const { user, impersonatedBy } = useAuth()
  const { brand_name: brandName } = usePublicConfig()
  const navigationItems = [
    ...(isSuperadmin(user, impersonatedBy)
      ? [{ to: '/admin/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard }]
      : []),
    { to: '/admin/users', label: t('nav.users'), icon: Users },
    { to: '/admin/organizations', label: t('nav.organizations'), icon: Building2 },
    { to: '/admin/setup', label: t('nav.setup'), icon: ListChecks },
  ]

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <Shield className="size-4" aria-hidden="true" />
            {t('title', { brand: brandName })}
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/app">
              <ArrowLeft className="size-4" aria-hidden="true" />
              {t('nav.back_to_app')}
            </Link>
          </Button>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4" aria-label={t('nav.label')}>
          {navigationItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm whitespace-nowrap',
                  isActive
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                )
              }
            >
              <item.icon className="size-4" aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
