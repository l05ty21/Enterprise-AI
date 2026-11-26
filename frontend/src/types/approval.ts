export type ApprovalStatus = 'pending' | 'approved' | 'rejected'
export type BusinessType = 'expense' | 'leave' | 'purchase' | 'other'

export interface Approval {
  id: number
  title: string
  business_type: BusinessType
  amount: number | null
  reason: string | null
  status: ApprovalStatus
  applicant_id: number
  applicant_name: string | null
  current_node: number
  current_approver_name: string | null
  can_decide: boolean
  created_at: string | null
}

export interface ApprovalTaskItem {
  id: number
  approver_id: number
  approver_name: string | null
  node_index: number
  status: string
  comment: string | null
  handled_at: string | null
}

export interface ApprovalAttachment {
  id: number
  filename: string
  file_size: number
  content_type: string | null
  uploader_name: string | null
  created_at: string | null
}

export interface ApprovalDetail extends Approval {
  tasks: ApprovalTaskItem[]
  attachments: ApprovalAttachment[]
}

export interface ApprovalCreatePayload {
  title: string
  business_type?: BusinessType
  amount?: number | null
  reason?: string | null
  approver_ids?: number[]
}

export interface ApprovalListQuery {
  page?: number
  page_size?: number
  scope?: 'all' | 'mine' | 'todo'
  status?: ApprovalStatus | ''
}
