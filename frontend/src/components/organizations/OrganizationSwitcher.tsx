import { Check, ChevronsUpDown, Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { CreateOrganizationForm } from '@/components/organizations/CreateOrganizationForm'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'

interface OrganizationSwitcherProps {
  onNavigate?: () => void
}

export function OrganizationSwitcher({ onNavigate }: OrganizationSwitcherProps) {
  const { t } = useTranslation('organizations')
  const { organizations } = useAuth()
  const { organization: currentOrganization } = useCurrentOrganization()
  const navigate = useNavigate()
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)

  function openOrganization(slug: string) {
    navigate(`/app/${slug}`)
    onNavigate?.()
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="w-full justify-between gap-2 px-2" aria-label={t('switcher.label')}>
            <span className="flex min-w-0 items-center gap-2">
              <OrganizationInitial name={currentOrganization.name} />
              <span className="truncate text-sm font-medium">{currentOrganization.name}</span>
            </span>
            <ChevronsUpDown className="size-4 shrink-0 opacity-60" aria-hidden />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel>{t('switcher.label')}</DropdownMenuLabel>
          {organizations.map((organization) => (
            <DropdownMenuItem key={organization.id} onSelect={() => openOrganization(organization.slug)}>
              <OrganizationInitial name={organization.name} />
              <span className="flex-1 truncate">{organization.name}</span>
              {organization.id === currentOrganization.id && <Check className="size-4" aria-hidden />}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setIsCreateDialogOpen(true)}>
            <Plus className="size-4" aria-hidden />
            {t('switcher.create')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('create.title')}</DialogTitle>
            <DialogDescription>{t('create.dialogDescription')}</DialogDescription>
          </DialogHeader>
          <CreateOrganizationForm
            onCreated={(organization) => {
              setIsCreateDialogOpen(false)
              openOrganization(organization.slug)
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  )
}

function OrganizationInitial({ name }: { name: string }) {
  return (
    <span
      aria-hidden
      className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground"
    >
      {name.charAt(0).toUpperCase()}
    </span>
  )
}
