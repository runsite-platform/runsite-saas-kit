import { ChevronDown, LogOut, Shield, UserRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/contexts/AuthContext'
import { isPlatformStaff } from '@/utils/platformRoles'

function initialsOf(displayName: string): string {
  const nameParts = displayName.trim().split(/\s+/).filter(Boolean)
  const initials = nameParts.slice(0, 2).map((namePart) => namePart[0]?.toUpperCase() ?? '')
  return initials.join('') || '?'
}

export function AccountMenu() {
  const { t } = useTranslation(['organizations', 'admin'])
  const { user, impersonatedBy, logout } = useAuth()
  if (!user) return null

  const displayName = user.full_name || user.email

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={t('organizations:nav.accountMenu')}
        className="flex items-center gap-2 rounded-full py-0.5 pr-2 pl-0.5 text-sm outline-none hover:bg-muted focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <Avatar size="sm" className="size-7">
          {user.avatar_url ? <AvatarImage src={user.avatar_url} alt="" /> : null}
          <AvatarFallback className="bg-primary text-[11px] font-semibold text-primary-foreground">
            {initialsOf(displayName)}
          </AvatarFallback>
        </Avatar>
        <span className="hidden max-w-40 truncate font-medium sm:inline">{displayName}</span>
        <ChevronDown className="size-3.5 text-muted-foreground" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="font-normal">
          <p className="truncate text-sm font-medium">{displayName}</p>
          {user.full_name ? <p className="truncate text-xs text-muted-foreground">{user.email}</p> : null}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/account">
            <UserRound className="size-4" aria-hidden />
            {t('organizations:nav.account')}
          </Link>
        </DropdownMenuItem>
        {isPlatformStaff(user, impersonatedBy) ? (
          <DropdownMenuItem asChild>
            <Link to="/admin">
              <Shield className="size-4" aria-hidden />
              {t('admin:menu.admin_panel')}
            </Link>
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => void logout()}>
          <LogOut className="size-4" aria-hidden />
          {t('organizations:nav.logout')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
