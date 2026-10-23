import { Archive, ArchiveRestore, Pencil, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { ConfirmActionDialog } from '@/components/organizations/ConfirmActionDialog'
import { ProjectFormDialog } from '@/components/projects/ProjectFormDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { useApiErrorToast } from '@/hooks/useApiErrorToast'
import { createProject, deleteProject, listProjects, updateProject } from '@/services/projectService'
import type { Project, ProjectInput, ProjectStatus } from '@/types/api'

type StatusFilter = ProjectStatus | 'all'

const STATUS_FILTERS: StatusFilter[] = ['active', 'archived', 'all']

export function ProjectsPage() {
  const { t, i18n } = useTranslation('projects')
  const { organization } = useCurrentOrganization()
  const showApiError = useApiErrorToast()
  const [projects, setProjects] = useState<Project[]>([])
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('active')
  const [isLoading, setIsLoading] = useState(true)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)

  const [reloadCounter, setReloadCounter] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true
    listProjects(organization.id, statusFilter === 'all' ? undefined : statusFilter)
      .then((loadedProjects) => {
        if (isCurrentRequest) setProjects(loadedProjects)
      })
      .catch((error: unknown) => {
        if (isCurrentRequest) showApiError(error)
      })
      .finally(() => {
        if (isCurrentRequest) setIsLoading(false)
      })
    return () => {
      isCurrentRequest = false
    }
  }, [organization.id, statusFilter, reloadCounter, showApiError])

  const reloadProjects = () => setReloadCounter((counter) => counter + 1)

  const changeStatusFilter = (value: string) => {
    setIsLoading(true)
    setStatusFilter(value as StatusFilter)
  }

  const openCreateDialog = () => {
    setEditingProject(null)
    setIsFormOpen(true)
  }

  const openEditDialog = (project: Project) => {
    setEditingProject(project)
    setIsFormOpen(true)
  }

  const saveProject = async (input: ProjectInput) => {
    try {
      if (editingProject) {
        await updateProject(organization.id, editingProject.id, input)
        toast.success(t('toast.updated'))
      } else {
        await createProject(organization.id, input)
        toast.success(t('toast.created'))
      }
      setIsFormOpen(false)
      reloadProjects()
    } catch (error) {
      showApiError(error)
    }
  }

  const toggleArchived = async (project: Project) => {
    const nextStatus: ProjectStatus = project.status === 'active' ? 'archived' : 'active'
    try {
      await updateProject(organization.id, project.id, { status: nextStatus })
      toast.success(t(nextStatus === 'archived' ? 'toast.archived' : 'toast.restored'))
      reloadProjects()
    } catch (error) {
      showApiError(error)
    }
  }

  const confirmDelete = async (project: Project) => {
    try {
      await deleteProject(organization.id, project.id)
      toast.success(t('toast.deleted'))
      reloadProjects()
    } catch (error) {
      showApiError(error)
    }
  }

  const dateFormatter = new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium' })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={statusFilter} onValueChange={changeStatusFilter}>
            <SelectTrigger className="w-36" aria-label={t('filter.label')}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_FILTERS.map((filterValue) => (
                <SelectItem key={filterValue} value={filterValue}>
                  {t(`filter.${filterValue}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={openCreateDialog}>
            <Plus className="size-4" aria-hidden />
            {t('new_project')}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">{t('loading')}</p>
      ) : projects.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          {statusFilter === 'active' ? t('empty') : t('empty_filtered')}
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('fields.name')}</TableHead>
                <TableHead>{t('fields.status')}</TableHead>
                <TableHead className="hidden md:table-cell">{t('fields.created_at')}</TableHead>
                <TableHead className="text-right">{t('fields.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell>
                    <div className="font-medium">{project.name}</div>
                    {project.description && (
                      <div className="line-clamp-1 text-sm text-muted-foreground">{project.description}</div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
                      {t(`status.${project.status}`)}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    {dateFormatter.format(new Date(project.created_at))}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={t('actions.edit')}
                        onClick={() => openEditDialog(project)}
                      >
                        <Pencil className="size-4" aria-hidden />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={t(project.status === 'active' ? 'actions.archive' : 'actions.restore')}
                        onClick={() => void toggleArchived(project)}
                      >
                        {project.status === 'active' ? (
                          <Archive className="size-4" aria-hidden />
                        ) : (
                          <ArchiveRestore className="size-4" aria-hidden />
                        )}
                      </Button>
                      <ConfirmActionDialog
                        trigger={
                          <Button variant="ghost" size="icon" aria-label={t('actions.delete')}>
                            <Trash2 className="size-4 text-destructive" aria-hidden />
                          </Button>
                        }
                        title={t('delete_dialog.title')}
                        description={t('delete_dialog.description', { name: project.name })}
                        confirmLabel={t('delete_dialog.confirm')}
                        onConfirm={() => confirmDelete(project)}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ProjectFormDialog
        open={isFormOpen}
        project={editingProject}
        onOpenChange={setIsFormOpen}
        onSubmit={saveProject}
      />
    </div>
  )
}
