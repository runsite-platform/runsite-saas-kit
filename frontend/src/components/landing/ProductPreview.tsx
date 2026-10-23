import {
  BarChart3,
  ChevronsUpDown,
  CreditCard,
  FileText,
  FolderKanban,
  Image,
  LayoutDashboard,
  Moon,
  ShieldCheck,
  Upload,
  Users,
} from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { KitPartId } from '@/components/landing/kitParts'
import { useBrandName } from '@/hooks/useBrandName'
import { cn } from '@/lib/utils'

const DESIGN_WIDTH = 880
const DESIGN_HEIGHT = 540
const CHART_VALUES = [3, 5, 4, 7, 6, 9, 8, 6, 10, 12, 9, 13, 15, 14]
const MEMBER_INITIALS = ['DK', 'MO', 'SL', 'AR']

interface ProductPreviewProps {
  activePart: KitPartId
}

interface PreviewRegionProps {
  part: KitPartId
  activePart: KitPartId
  className?: string
  children: ReactNode
}

function PreviewRegion({ part, activePart, className, children }: PreviewRegionProps) {
  const isActive = part === activePart
  return (
    <div
      data-part={part}
      className={cn(
        'relative rounded-lg transition-[box-shadow,background-color] duration-300 motion-reduce:transition-none',
        isActive && 'bg-highlight/15 shadow-[0_0_0_2px_var(--highlight),0_0_0_7px_color-mix(in_oklch,var(--highlight)_25%,transparent)]',
        className,
      )}
    >
      {children}
    </div>
  )
}

function useFitScale(designWidth: number) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  useEffect(() => {
    const container = containerRef.current
    if (!container || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(([entry]) => {
      setScale(Math.min(1, entry.contentRect.width / designWidth))
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [designWidth])

  return { containerRef, scale }
}

export function ProductPreview({ activePart }: ProductPreviewProps) {
  const { t } = useTranslation('landing')
  const brandName = useBrandName()
  const { containerRef, scale } = useFitScale(DESIGN_WIDTH)
  const highestChartValue = Math.max(...CHART_VALUES)

  const navigationItems = [
    { icon: LayoutDashboard, label: t('landing:preview.nav.overview'), isCurrent: true },
    { icon: FolderKanban, label: t('landing:preview.nav.projects'), isCurrent: false },
    { icon: Upload, label: t('landing:preview.nav.files'), isCurrent: false },
    { icon: Users, label: t('landing:preview.nav.members'), isCurrent: false },
    { icon: CreditCard, label: t('landing:preview.nav.billing'), isCurrent: false },
  ]
  const statTiles = [
    { label: t('landing:preview.stats.projects'), value: '24' },
    { label: t('landing:preview.stats.members'), value: '4' },
    { label: t('landing:preview.stats.storage'), value: '64 MB' },
  ]
  const recentProjects = [
    { name: t('landing:preview.projectNames.first'), icon: FileText, updated: '2h' },
    { name: t('landing:preview.projectNames.second'), icon: BarChart3, updated: '1d' },
    { name: t('landing:preview.projectNames.third'), icon: Image, updated: '3d' },
  ]

  return (
    <div ref={containerRef} className="w-full" role="img" aria-label={t('landing:preview.windowLabel')}>
      <div style={{ height: DESIGN_HEIGHT * scale }} className="relative">
        <div
          aria-hidden="true"
          style={{ width: DESIGN_WIDTH, height: DESIGN_HEIGHT, transform: `scale(${scale})` }}
          className="absolute top-0 left-0 origin-top-left overflow-hidden rounded-2xl border bg-card text-[13px] text-card-foreground shadow-[0_1px_0_var(--border),0_24px_60px_-28px_color-mix(in_oklch,var(--foreground)_35%,transparent)]"
        >
          <div className="flex h-11 items-center gap-3 border-b bg-muted/50 px-4">
            <div className="flex gap-1.5">
              <span className="size-2.5 rounded-full bg-foreground/15" />
              <span className="size-2.5 rounded-full bg-foreground/15" />
              <span className="size-2.5 rounded-full bg-foreground/15" />
            </div>
            <div className="mx-auto w-64 rounded-md border bg-background px-3 py-1 text-center text-xs text-muted-foreground">
              {t('landing:preview.url', { brandName: brandName.toLowerCase().replace(/\s+/g, '') })}
            </div>
            <PreviewRegion part="theming" activePart={activePart} className="flex items-center gap-2 px-2 py-1">
              <span className="flex -space-x-1">
                <span className="size-3.5 rounded-full border-2 border-card bg-primary" />
                <span className="size-3.5 rounded-full border-2 border-card bg-highlight" />
                <span className="size-3.5 rounded-full border-2 border-card bg-foreground" />
              </span>
              <Moon className="size-3.5 text-muted-foreground" />
            </PreviewRegion>
            <PreviewRegion part="auth" activePart={activePart} className="flex items-center gap-2 px-2 py-1">
              <span className="rounded-full bg-primary/12 px-2 py-0.5 text-[11px] font-medium text-primary">
                {t('landing:preview.verified')}
              </span>
              <span className="flex size-6 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                DK
              </span>
            </PreviewRegion>
          </div>

          <div className="grid h-[calc(100%-2.75rem)] grid-cols-[200px_1fr]">
            <aside className="flex flex-col gap-4 border-r bg-muted/30 p-3">
              <PreviewRegion part="organizations" activePart={activePart} className="space-y-3 p-2">
                <div className="flex items-center gap-2 rounded-md border bg-background px-2 py-1.5">
                  <span className="flex size-6 items-center justify-center rounded bg-foreground text-[11px] font-bold text-background">
                    N
                  </span>
                  <span className="flex-1 font-medium">{t('landing:preview.organization')}</span>
                  <ChevronsUpDown className="size-3.5 text-muted-foreground" />
                </div>
                <div className="flex -space-x-1.5 pl-1">
                  {MEMBER_INITIALS.map((initials) => (
                    <span
                      key={initials}
                      className="flex size-6 items-center justify-center rounded-full border-2 border-card bg-secondary text-[9px] font-semibold"
                    >
                      {initials}
                    </span>
                  ))}
                </div>
              </PreviewRegion>

              <nav className="space-y-0.5 px-2">
                {navigationItems.map((navigationItem) => (
                  <div
                    key={navigationItem.label}
                    className={cn(
                      'flex items-center gap-2 rounded-md px-2 py-1.5 text-muted-foreground',
                      navigationItem.isCurrent && 'bg-background font-medium text-foreground shadow-xs',
                    )}
                  >
                    <navigationItem.icon className="size-3.5" />
                    {navigationItem.label}
                  </div>
                ))}
              </nav>

              <PreviewRegion part="admin" activePart={activePart} className="mx-2 px-2 py-1.5">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <ShieldCheck className="size-3.5" />
                  {t('landing:preview.nav.admin')}
                </div>
              </PreviewRegion>

              <PreviewRegion part="billing" activePart={activePart} className="mt-auto">
                <div className="space-y-2 rounded-lg border bg-background p-3">
                  <div className="flex items-baseline justify-between">
                    <span className="font-semibold">{t('landing:preview.plan')}</span>
                    <span className="text-[11px] text-muted-foreground">{t('landing:preview.trialLeft')}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div className="h-full w-[15%] rounded-full bg-primary" />
                  </div>
                  <div className="rounded-md bg-primary py-1.5 text-center text-xs font-medium text-primary-foreground">
                    {t('landing:preview.upgrade')}
                  </div>
                </div>
              </PreviewRegion>
            </aside>

            <main className="flex flex-col gap-4 p-5">
              <p className="text-lg font-bold tracking-tight">{t('landing:preview.greeting')}</p>

              <PreviewRegion part="dashboard" activePart={activePart} className="space-y-3 p-1">
                <div className="grid grid-cols-3 gap-3">
                  {statTiles.map((statTile) => (
                    <div key={statTile.label} className="rounded-lg border bg-background px-3 py-2.5">
                      <p className="text-[11px] text-muted-foreground">{statTile.label}</p>
                      <p className="mt-0.5 text-xl font-bold tabular-nums">{statTile.value}</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-lg border bg-background p-3">
                  <p className="mb-2 text-[11px] text-muted-foreground">{t('landing:preview.chartTitle')}</p>
                  <div className="flex h-20 items-end gap-1.5">
                    {CHART_VALUES.map((chartValue, dayIndex) => (
                      <span
                        key={dayIndex}
                        style={{ height: `${(chartValue / highestChartValue) * 100}%` }}
                        className={cn(
                          'flex-1 rounded-t-[3px]',
                          dayIndex === CHART_VALUES.length - 1 ? 'bg-primary' : 'bg-primary/35',
                        )}
                      />
                    ))}
                  </div>
                </div>
              </PreviewRegion>

              <div className="grid flex-1 grid-cols-[1.4fr_1fr] gap-3">
                <PreviewRegion part="modules" activePart={activePart} className="p-1">
                  <div className="h-full rounded-lg border bg-background p-3">
                    <p className="mb-2 text-[11px] text-muted-foreground">{t('landing:preview.projectsTitle')}</p>
                    <ul className="divide-y">
                      {recentProjects.map((recentProject) => (
                        <li key={recentProject.name} className="flex items-center gap-2 py-1.5">
                          <recentProject.icon className="size-3.5 text-muted-foreground" />
                          <span className="flex-1">{recentProject.name}</span>
                          <span className="text-[11px] text-muted-foreground tabular-nums">{recentProject.updated}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </PreviewRegion>
                <PreviewRegion part="files" activePart={activePart} className="p-1">
                  <div className="flex h-full flex-col justify-between rounded-lg border bg-background p-3">
                    <div className="flex gap-2">
                      {[FileText, Image, FileText].map((FileIcon, fileIndex) => (
                        <span
                          key={fileIndex}
                          className="flex size-9 items-center justify-center rounded-md border bg-muted/50 text-muted-foreground"
                        >
                          <FileIcon className="size-4" />
                        </span>
                      ))}
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[11px] text-muted-foreground">
                        <span>{t('landing:preview.stats.storage')}</span>
                        <span className="tabular-nums">{t('landing:preview.storageOf')}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                        <div className="h-full w-[64%] rounded-full bg-primary" />
                      </div>
                    </div>
                  </div>
                </PreviewRegion>
              </div>
            </main>
          </div>
        </div>
      </div>
    </div>
  )
}
