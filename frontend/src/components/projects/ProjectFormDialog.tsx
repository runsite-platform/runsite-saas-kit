import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { Project, ProjectInput } from '@/types/api'

const projectFormSchema = z.object({
  name: z.string().trim().min(1, 'name_required').max(200, 'name_too_long'),
  description: z.string().max(5000, 'description_too_long'),
})

type ProjectFormValues = z.infer<typeof projectFormSchema>

interface ProjectFormDialogProps {
  open: boolean
  project: Project | null
  onOpenChange: (open: boolean) => void
  onSubmit: (input: ProjectInput) => Promise<void>
}

export function ProjectFormDialog({ open, project, onOpenChange, onSubmit }: ProjectFormDialogProps) {
  const { t } = useTranslation('projects')
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: { name: '', description: '' },
  })

  useEffect(() => {
    if (open) {
      reset({ name: project?.name ?? '', description: project?.description ?? '' })
    }
  }, [open, project, reset])

  const submitForm = handleSubmit(async (values) => {
    const description = values.description.trim()
    await onSubmit({ name: values.name, description: description || null })
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>{project ? t('edit_title') : t('create_title')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={submitForm} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="project-name">{t('fields.name')}</Label>
            <Input id="project-name" autoFocus aria-invalid={Boolean(errors.name)} {...register('name')} />
            {errors.name?.message && (
              <p className="text-sm text-destructive">{t(`validation.${errors.name.message}`)}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-description">{t('fields.description')}</Label>
            <Textarea
              id="project-description"
              rows={4}
              aria-invalid={Boolean(errors.description)}
              {...register('description')}
            />
            {errors.description?.message && (
              <p className="text-sm text-destructive">{t(`validation.${errors.description.message}`)}</p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t('actions.cancel')}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {t('actions.save')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
