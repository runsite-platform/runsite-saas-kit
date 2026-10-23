import { ImageUp, Trash2 } from 'lucide-react'
import { type ChangeEvent, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { classifyApiError } from '@/utils/classifyApiError'

const IMAGE_CONTENT_TYPES = ['image/png', 'image/jpeg', 'image/webp']
const MAX_IMAGE_BYTES = 2 * 1024 * 1024

interface ImageUploadFieldProps {
  imageUrl: string | null
  fallbackText: string
  onUpload: (file: File) => Promise<void>
  onRemove: () => Promise<void>
}

export function ImageUploadField({ imageUrl, fallbackText, onUpload, onRemove }: ImageUploadFieldProps) {
  const { t } = useTranslation(['files', 'errors'])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [errorCode, setErrorCode] = useState<string | null>(null)

  const runAction = async (action: () => Promise<void>) => {
    setIsBusy(true)
    setErrorCode(null)
    try {
      await action()
    } catch (error) {
      const result = classifyApiError(error)
      setErrorCode(result.kind === 'message' ? result.code : null)
    } finally {
      setIsBusy(false)
    }
  }

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }
    if (!IMAGE_CONTENT_TYPES.includes(file.type)) {
      setErrorCode('unsupported_file_type')
      return
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setErrorCode('file_too_large')
      return
    }
    await runAction(() => onUpload(file))
  }

  return (
    <div className="flex flex-wrap items-center gap-4">
      <Avatar className="size-16">
        {imageUrl && <AvatarImage src={imageUrl} alt="" />}
        <AvatarFallback className="text-lg">{fallbackText}</AvatarFallback>
      </Avatar>
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept={IMAGE_CONTENT_TYPES.join(',')}
            className="sr-only"
            tabIndex={-1}
            onChange={(event) => void handleFileChange(event)}
          />
          <Button type="button" variant="outline" disabled={isBusy} onClick={() => fileInputRef.current?.click()}>
            <ImageUp className="size-4" aria-hidden />
            {imageUrl ? t('image.replace') : t('image.upload')}
          </Button>
          {imageUrl && (
            <Button type="button" variant="ghost" disabled={isBusy} onClick={() => void runAction(onRemove)}>
              <Trash2 className="size-4" aria-hidden />
              {t('image.remove')}
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">{t('image.hint')}</p>
        {errorCode && (
          <p role="alert" className="text-sm text-destructive">
            {t(`errors:${errorCode}`, { defaultValue: t('errors:unknown_error') })}
          </p>
        )}
      </div>
    </div>
  )
}
