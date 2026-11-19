import { apiClient } from './client'

import type { MessageResponse, PageResult } from '@/types/api'
import type { UserCreatePayload, UserItem, UserQuery, UserUpdatePayload } from '@/types/user'

export const usersApi = {
  list(params: UserQuery) {
    return apiClient.get<PageResult<UserItem>>('/users', { params })
  },

  detail(id: number) {
    return apiClient.get<UserItem>(`/users/${id}`)
  },

  create(payload: UserCreatePayload) {
    return apiClient.post<UserItem>('/users', payload)
  },

  update(id: number, payload: UserUpdatePayload) {
    return apiClient.put<UserItem>(`/users/${id}`, payload)
  },

  disable(id: number) {
    return apiClient.delete<MessageResponse>(`/users/${id}`)
  },
}
