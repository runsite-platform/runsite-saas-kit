import { Link, Outlet } from 'react-router-dom'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { LogoMark } from '@/components/brand/LogoMark'

export function AuthLayout() {
  const { brand_name: brandName } = usePublicConfig()
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted/40 px-4 py-10">
      <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
        <LogoMark />
        {brandName}
      </Link>
      <main className="w-full max-w-sm">
        <Outlet />
      </main>
    </div>
  )
}
