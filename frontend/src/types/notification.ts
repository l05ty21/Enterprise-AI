export interface NotificationItem {
  id: number
  title: string
  content: string | null
  type: string | null
  link_type: string | null
  link_id: number | null
  is_read: boolean
  created_at: string | null
}

export interface UnreadCount {
  count: number
}
