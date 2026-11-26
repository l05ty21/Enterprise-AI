import { apiClient } from './client'

import type { AttachmentItem } from '@/types/attachment'

export const attachmentsApi = {
  listTickets(ticketId: number) {
    return apiClient.get<AttachmentItem[]>(`/attachments/tickets/${ticketId}`)
  },

  uploadTicket(ticketId: number, file: File) {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<AttachmentItem>(`/attachments/tickets/${ticketId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  listApprovals(approvalId: number) {
    return apiClient.get<AttachmentItem[]>(`/attachments/approvals/${approvalId}`)
  },

  uploadApproval(approvalId: number, file: File) {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<AttachmentItem>(`/attachments/approvals/${approvalId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  async download(id: number, filename: string): Promise<void> {
    const { data } = await apiClient.get<Blob>(`/attachments/${id}/download`, {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  },

  remove(id: number) {
    return apiClient.delete(`/attachments/${id}`)
  },
}
