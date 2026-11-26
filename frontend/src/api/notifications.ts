import { apiClient } from './client'

import type { PageResult } from '@/types/api'
import type { NotificationItem, UnreadCount } from '@/types/notification'

export const notificationsApi = {
  list(params?: { page?: number; page_size?: number; unread_only?: boolean }) {
    return apiClient.get<PageResult<NotificationItem>>('/notifications', { params })
  },

  unreadCount() {
    return apiClient.get<UnreadCount>('/notifications/unread-count')
  },

  markRead(id: number) {
    return apiClient.post<NotificationItem>(`/notifications/${id}/read`)
  },

  markAllRead() {
    return apiClient.post('/notifications/read-all')
  },
}
