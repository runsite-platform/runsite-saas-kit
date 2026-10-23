import {
  CreditCard,
  Files,
  FolderKanban,
  LayoutDashboard,
  Menu,
  Settings,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router-dom'
import { VerifyEmailBanner } from '@/components/auth/VerifyEmailBanner'
import { SidebarPlanCard } from '@/components/billing/SidebarPlanCard'
import { UpgradeDialog } from '@/components/billing/UpgradeDialog'
import { LogoMark } from '@/components/brand/LogoMark'
import { AccountMenu } from '@/components/layout/AccountMenu'
import { NotificationBell } from '@/components/notifications/NotificationBell'
import { OrganizationSwitcher } from '@/components/organizations/OrganizationSwitcher'
import { ThemeToggle } from '@/components/theme/ThemeToggle'
import { Button } from '@/components/ui/button'
import { NotificationsProvider } from '@/contexts/NotificationsContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { cn } from '@/lib/utils'
import type { OrgAction } from '@/utils/orgPermissions'

interface NavigationVisibility {
  fileUploadsEnabled: boolean
  can: (action: OrgAction) => boolean
}

interface AppNavigationItem {
  path: string
  labelKey: string
  icon: LucideIcon
  isVisible?: (visibility: NavigationVisibility) => boolean
}

const APP_NAVIGATION_ITEMS: AppNavigationItem[] = [
  { path: '', labelKey: 'nav.overview', icon: LayoutDashboard },
  { path: 'projects', labelKey: 'nav.projects', icon: FolderKanban },
  { path: 'files', labelKey: 'nav.files', icon: Files, isVisible: ({ fileUploadsEnabled }) => fileUploadsEnabled },
  { path: 'members', labelKey: 'nav.members', icon: Users },
  { path: 'billing', labelKey: 'nav.billing', icon: CreditCard, isVisible: ({ can }) => can('manage_billing') },
  { path: 'settings', labelKey: 'nav.settings', icon: Settings, isVisible: ({ can }) => can('manage_settings') },
]

export default function AppLayout() {
  const { t } = useTranslation('organizations')
  const { organization } = useCurrentOrganization()
  const [isMobileNavigationOpen, setIsMobileNavigationOpen] = useState(false)
  const closeMobileNavigation = () => setIsMobileNavigationOpen(false)

  return (
    <NotificationsProvider>
      <div className="min-h-svh bg-background md:grid md:grid-cols-[15rem_1fr]">
        <aside className="hidden border-r bg-muted/30 md:sticky md:top-0 md:flex md:h-svh md:flex-col">
          <AppSidebar />
        </aside>

        {isMobileNavigationOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <button
              type="button"
              aria-label={t('nav.closeMenu')}
              className="absolute inset-0 bg-black/40"
              onClick={closeMobileNavigation}
            />
            <aside className="relative z-50 flex h-full w-72 max-w-[85vw] flex-col bg-muted shadow-xl">
              <div className="flex justify-end p-2">
                <Button variant="ghost" size="icon" aria-label={t('nav.closeMenu')} onClick={closeMobileNavigation}>
                  <X className="size-5" aria-hidden />
                </Button>
              </div>
              <AppSidebar onNavigate={closeMobileNavigation} />
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-col">
          <header className="sticky top-0 z-30 flex h-12 items-center gap-2 border-b bg-background/85 px-3 backdrop-blur md:px-6">
            <Button
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              aria-label={t('nav.openMenu')}
              onClick={() => setIsMobileNavigationOpen(true)}
            >
              <Menu className="size-4" aria-hidden />
            </Button>
            <span className="truncate text-sm font-medium md:hidden">{organization.name}</span>
            <div className="ml-auto flex items-center gap-1">
              <NotificationBell notificationsPath={`/app/${organization.slug}/notifications`} />
              <ThemeToggle />
              <AccountMenu />
            </div>
          </header>

          <main className="min-w-0 flex-1 space-y-6 px-4 py-6 md:px-8 md:py-8">
            <VerifyEmailBanner />
            <Outlet />
          </main>
        </div>
        <UpgradeDialog />
      </div>
    </NotificationsProvider>
  )
}

function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation('organizations')
  const { organization, can } = useCurrentOrganization()
  const { brand_name: brandName, features } = usePublicConfig()
  const basePath = `/app/${organization.slug}`
  const visibleItems = APP_NAVIGATION_ITEMS.filter(
    (item) => !item.isVisible || item.isVisible({ fileUploadsEnabled: features.file_uploads, can }),
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-3">
      <div className="flex h-9 items-center gap-2 px-2 text-sm font-semibold">
        <LogoMark className="size-6" />
        {brandName}
      </div>
      <OrganizationSwitcher onNavigate={onNavigate} />
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto" aria-label={t('nav.label')}>
        {visibleItems.map((item) => (
          <NavLink
            key={item.labelKey}
            to={item.path ? `${basePath}/${item.path}` : basePath}
            end={!item.path}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors',
                isActive
                  ? 'bg-background font-medium text-foreground shadow-xs ring-1 ring-border'
                  : 'text-muted-foreground hover:bg-background/60 hover:text-foreground',
              )
            }
          >
            <item.icon className="size-4" aria-hidden />
            {t(item.labelKey)}
          </NavLink>
        ))}
      </nav>
      <SidebarPlanCard onNavigate={onNavigate} />
    </div>
  )
}
