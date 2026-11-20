export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'
export type TicketStatus = 'pending' | 'processing' | 'resolved' | 'closed'

export interface Ticket {
  id: number
  ticket_no: string
  title: string
  description: string | null
  priority: TicketPriority
  status: TicketStatus
  creator_id: number
  creator_name: string | null
  assignee_id: number | null
  assignee_name: string | null
  created_at: string | null
  updated_at: string | null
}

export interface TicketCommentItem {
  id: number
  user_id: number
  user_name: string | null
  content: string
  created_at: string | null
}

export interface TicketHistoryItem {
  id: number
  operator_id: number
  operator_name: string | null
  old_status: string | null
  new_status: string | null
  remark: string | null
  created_at: string | null
}

export interface TicketDetail extends Ticket {
  comments: TicketCommentItem[]
  histories: TicketHistoryItem[]
}

export interface TicketCreatePayload {
  title: string
  description?: string | null
  priority?: TicketPriority
}

export interface TicketUpdatePayload {
  status?: TicketStatus
  assignee_id?: number | null
  priority?: TicketPriority
  remark?: string | null
}

export interface TicketListQuery {
  page?: number
  page_size?: number
  keyword?: string
  status?: TicketStatus | ''
  priority?: TicketPriority | ''
  mine?: boolean
}
