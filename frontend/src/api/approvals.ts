import { apiClient } from './client'

import type { PageResult } from '@/types/api'
import type {
  Approval,
  ApprovalCreatePayload,
  ApprovalDetail,
  ApprovalListQuery,
} from '@/types/approval'

export const approvalsApi = {
  list(params: ApprovalListQuery) {
    return apiClient.get<PageResult<Approval>>('/approvals', { params })
  },

  create(payload: ApprovalCreatePayload) {
    return apiClient.post<Approval>('/approvals', payload)
  },

  detail(id: number) {
    return apiClient.get<ApprovalDetail>(`/approvals/${id}`)
  },

  decide(id: number, action: 'approve' | 'reject', comment?: string) {
    return apiClient.post<ApprovalDetail>(`/approvals/${id}/decision`, {
      action,
      comment: comment || null,
    })
  },
}
