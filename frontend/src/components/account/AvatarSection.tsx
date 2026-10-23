import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { ImageUploadField } from '@/components/shared/ImageUploadField'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { usePublicConfig } from '@/contexts/PublicConfigContext'
import { meService } from '@/services/me'

export function AvatarSection() {
  const { t } = useTranslation('account')
  const { user, reloadMe } = useAuth()
  const { features } = usePublicConfig()

  if (!user || !features.file_uploads) {
    return null
  }

  const initials = (user.full_name || user.email).slice(0, 2).toUpperCase()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('avatar.title')}</CardTitle>
        <CardDescription>{t('avatar.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ImageUploadField
          imageUrl={user.avatar_url}
          fallbackText={initials}
          onUpload={async (file) => {
            await meService.uploadAvatar(file)
            await reloadMe()
            toast.success(t('avatar.updated'))
          }}
          onRemove={async () => {
            await meService.removeAvatar()
            await reloadMe()
            toast.success(t('avatar.removed'))
          }}
        />
      </CardContent>
    </Card>
  )
}
