export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ApiError {
  code: string
  message: string
  detail?: unknown
  path?: string
}

export interface MessageResponse {
  message: string
}

export interface PageQuery {
  page?: number
  page_size?: number
}
