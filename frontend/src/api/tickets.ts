import { apiClient } from './client'

import type { PageResult } from '@/types/api'
import type {
  Ticket,
  TicketCommentItem,
  TicketCreatePayload,
  TicketDetail,
  TicketListQuery,
  TicketUpdatePayload,
} from '@/types/ticket'

export const ticketsApi = {
  list(params: TicketListQuery) {
    return apiClient.get<PageResult<Ticket>>('/tickets', { params })
  },

  create(payload: TicketCreatePayload) {
    return apiClient.post<Ticket>('/tickets', payload)
  },

  detail(id: number) {
    return apiClient.get<TicketDetail>(`/tickets/${id}`)
  },

  update(id: number, payload: TicketUpdatePayload) {
    return apiClient.patch<TicketDetail>(`/tickets/${id}`, payload)
  },

  addComment(id: number, content: string) {
    return apiClient.post<TicketCommentItem>(`/tickets/${id}/comments`, { content })
  },
}
