import { Download, Trash2, Upload } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { ConfirmActionDialog } from '@/components/organizations/ConfirmActionDialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAuth } from '@/contexts/AuthContext'
import { useCurrentOrganization } from '@/contexts/OrganizationContext'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { useApiErrorToast } from '@/hooks/useApiErrorToast'
import { MAX_FILE_BYTES, deleteFile, getDownloadUrl, listFiles, uploadFile } from '@/services/fileService'
import type { StoredFile } from '@/types/api'
import { formatFileSize } from '@/utils/formatFileSize'

export function FilesPage() {
  const { t } = useTranslation('files')
  const { features } = usePublicConfig()

  if (!features.file_uploads) {
    return (
      <div className="space-y-2 rounded-lg border border-dashed p-10 text-center">
        <h1 className="text-lg font-semibold">{t('disabled_title')}</h1>
        <p className="text-sm text-muted-foreground">{t('disabled_description')}</p>
      </div>
    )
  }
  return <FileManager />
}

function FileManager() {
  const { t, i18n } = useTranslation(['files', 'errors'])
  const { organization, can } = useCurrentOrganization()
  const { user } = useAuth()
  const showApiError = useApiErrorToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [storedFiles, setStoredFiles] = useState<StoredFile[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [reloadCounter, setReloadCounter] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true
    listFiles(organization.id)
      .then((loadedFiles) => {
        if (isCurrentRequest) setStoredFiles(loadedFiles)
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
  }, [organization.id, reloadCounter, showApiError])

  const reloadFiles = () => setReloadCounter((counter) => counter + 1)

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedFile) {
      return
    }
    if (selectedFile.size > MAX_FILE_BYTES) {
      toast.error(t('errors:file_too_large'))
      return
    }
    setIsUploading(true)
    try {
      await uploadFile(organization.id, selectedFile)
      toast.success(t('toast.uploaded'))
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      reloadFiles()
    } catch (error) {
      showApiError(error)
    } finally {
      setIsUploading(false)
    }
  }

  const handleDownload = async (storedFile: StoredFile) => {
    const downloadWindow = window.open('', '_blank')
    try {
      const { url } = await getDownloadUrl(organization.id, storedFile.id)
      if (downloadWindow) {
        downloadWindow.opener = null
        downloadWindow.location.href = url
      } else {
        window.location.assign(url)
      }
    } catch (error) {
      downloadWindow?.close()
      showApiError(error)
    }
  }

  const confirmDelete = async (storedFile: StoredFile) => {
    try {
      await deleteFile(organization.id, storedFile.id)
      toast.success(t('toast.deleted'))
      reloadFiles()
    } catch (error) {
      showApiError(error)
    }
  }

  const canDelete = (storedFile: StoredFile) => can('delete_any_file') || storedFile.uploaded_by_id === user?.id
  const dateFormatter = new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
        <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
      </div>

      <form
        onSubmit={(event) => void handleUpload(event)}
        className="flex flex-wrap items-end gap-3 rounded-lg border p-4"
      >
        <div className="min-w-0 flex-1 space-y-2">
          <Label htmlFor="file-upload">{t('choose_file')}</Label>
          <Input
            id="file-upload"
            ref={fileInputRef}
            type="file"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
        </div>
        <Button type="submit" disabled={!selectedFile || isUploading}>
          <Upload className="size-4" aria-hidden />
          {isUploading ? t('uploading') : t('upload')}
        </Button>
      </form>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">{t('loading')}</p>
      ) : storedFiles.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          {t('empty')}
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('fields.name')}</TableHead>
                <TableHead className="w-28">{t('fields.size')}</TableHead>
                <TableHead className="hidden md:table-cell">{t('fields.uploaded_at')}</TableHead>
                <TableHead className="text-right">{t('fields.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {storedFiles.map((storedFile) => (
                <TableRow key={storedFile.id}>
                  <TableCell className="max-w-xs truncate font-medium">{storedFile.name}</TableCell>
                  <TableCell className="tabular-nums">{formatFileSize(storedFile.size_bytes)}</TableCell>
                  <TableCell className="hidden md:table-cell">
                    {dateFormatter.format(new Date(storedFile.created_at))}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={t('actions.download')}
                        onClick={() => void handleDownload(storedFile)}
                      >
                        <Download className="size-4" aria-hidden />
                      </Button>
                      {canDelete(storedFile) && (
                        <ConfirmActionDialog
                          trigger={
                            <Button variant="ghost" size="icon" aria-label={t('actions.delete')}>
                              <Trash2 className="size-4 text-destructive" aria-hidden />
                            </Button>
                          }
                          title={t('delete_dialog.title')}
                          description={t('delete_dialog.description', { name: storedFile.name })}
                          confirmLabel={t('delete_dialog.confirm')}
                          onConfirm={() => confirmDelete(storedFile)}
                        />
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
