export type ChatRole = 'system' | 'user' | 'assistant'

export interface ChatMessageItem {
  role: ChatRole
  content: string
}

export interface ChatPayload {
  messages: ChatMessageItem[]
  system_prompt?: string
  temperature?: number
  max_tokens?: number
}

export interface ChatResponse {
  content: string
  model: string
  input_tokens: number
  output_tokens: number
  latency_ms: number
}

export interface StreamHandlers {
  onDelta: (text: string) => void
  onDone?: (meta?: { model?: string }) => void
  onError?: (message: string) => void
}
