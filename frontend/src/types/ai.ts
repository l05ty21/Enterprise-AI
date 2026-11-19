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

export type ModelType = 'llm' | 'embedding' | 'rerank'

export interface ModelConfig {
  id: number
  organization_id: number
  model_name: string
  provider: string
  model_type: ModelType
  base_url: string | null
  api_key_masked: string | null
  has_api_key: boolean
  is_default: boolean
  is_enabled: boolean
  parameters: Record<string, unknown> | null
  created_at: string | null
}

export interface ModelConfigPayload {
  model_name: string
  provider: string
  model_type?: ModelType
  base_url?: string | null
  api_key?: string
  is_default?: boolean
  is_enabled?: boolean
  parameters?: Record<string, unknown> | null
}

export interface ProviderOption {
  provider: string
  label: string
  base_url: string
  default_model: string
  requires_api_key: boolean
}

export interface UsageRow {
  model_name: string | null
  status: string | null
  calls: number
  input_tokens: number
  output_tokens: number
  avg_latency_ms: number
}

export interface UsageSummary {
  days: number
  calls: number
  input_tokens: number
  output_tokens: number
  items: UsageRow[]
}
