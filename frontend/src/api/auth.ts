import { apiClient } from './client'

import type { MessageResponse } from '@/types/api'
import type {
  CurrentUser,
  LoginPayload,
  PasswordPayload,
  ProfilePayload,
  TokenPair,
} from '@/types/user'

export const authApi = {
  login(payload: LoginPayload) {
    return apiClient.post<TokenPair>('/auth/login', payload)
  },

  logout(refreshToken?: string | null) {
    return apiClient.post<MessageResponse>('/auth/logout', {
      refresh_token: refreshToken ?? undefined,
    })
  },

  me() {
    return apiClient.get<CurrentUser>('/auth/me')
  },

  updateProfile(payload: ProfilePayload) {
    return apiClient.put<CurrentUser>('/auth/me', payload)
  },

  changePassword(payload: PasswordPayload) {
    return apiClient.put<MessageResponse>('/auth/me/password', payload)
  },
}
