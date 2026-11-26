export interface AttachmentItem {
  id: number
  biz_type?: string
  biz_id?: number
  filename: string
  file_size: number
  content_type: string | null
  uploader_id?: number
  uploader_name: string | null
  created_at: string | null
}
