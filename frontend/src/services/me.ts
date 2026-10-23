import type { AvatarResponse, MeResponse, StatusResponse, User } from '@/types/api'
import { fetchApi } from '@/utils/fetchApi'

export interface ChangePasswordInput {
  current_password: string | null
  new_password: string
}

export const meService = {
  getMe(): Promise<MeResponse> {
    return fetchApi<MeResponse>('/me')
  },

  updateProfile(fullName: string): Promise<User> {
    return fetchApi<User>('/me', { method: 'PATCH', body: { full_name: fullName } })
  },

  changePassword(input: ChangePasswordInput): Promise<StatusResponse> {
    return fetchApi<StatusResponse>('/me/password', { method: 'POST', body: input })
  },

  uploadAvatar(file: File): Promise<AvatarResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return fetchApi<AvatarResponse>('/me/avatar', { method: 'PUT', formData })
  },

  removeAvatar(): Promise<void> {
    return fetchApi<void>('/me/avatar', { method: 'DELETE' })
  },
}
