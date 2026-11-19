export interface KnowledgeBase {
  id: number
  name: string
  description: string | null
  owner_id: number
  visibility: string
  status: number
  document_count: number
  chunk_count: number
  created_at: string | null
}

export interface KnowledgeBasePayload {
  name: string
  description?: string | null
  visibility?: string
}

export interface KBDocument {
  id: number
  kb_id: number
  filename: string
  file_type: string | null
  file_size: number | null
  status: string
  chunk_count: number
  error_message: string | null
  created_at: string | null
}

export interface SearchHit {
  chunk_id: number
  document_id: number
  filename: string
  content: string
  score: number
}

export interface SearchPayload {
  query: string
  kb_ids?: number[] | null
  top_k?: number
}

export interface Citation {
  document_id: number
  filename: string
  chunk_id: number
  score: number
  snippet: string
}
