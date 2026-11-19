import { apiClient } from './client'

import type {
  ChatPayload,
  ChatResponse,
  Citation,
  ModelConfig,
  ModelConfigPayload,
  ProviderOption,
  StreamHandlers,
  UsageSummary,
} from '@/types/ai'
import type { MessageResponse } from '@/types/api'
import { getAccessToken } from '@/utils/token'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const aiApi = {
  // ---------------------------------------------------------------- 配置管理
  providers() {
    return apiClient.get<ProviderOption[]>('/ai/providers')
  },

  listModels() {
    return apiClient.get<ModelConfig[]>('/ai/models')
  },

  createModel(payload: ModelConfigPayload) {
    return apiClient.post<ModelConfig>('/ai/models', payload)
  },

  updateModel(id: number, payload: Partial<ModelConfigPayload>) {
    return apiClient.put<ModelConfig>(`/ai/models/${id}`, payload)
  },

  deleteModel(id: number) {
    return apiClient.delete<MessageResponse>(`/ai/models/${id}`)
  },

  usage(days = 7) {
    return apiClient.get<UsageSummary>('/ai/usage', { params: { days } })
  },
  /** 非流式对话，一次性返回完整结果 */
  chat(payload: ChatPayload) {
    return apiClient.post<ChatResponse>('/ai/chat', payload, { timeout: 120000 })
  },

  /**
   * 流式对话（SSE）。
   * 浏览器端用 fetch + ReadableStream，axios 拿不到增量数据。
   */
  async streamChat(
    payload: ChatPayload,
    handlers: StreamHandlers,
    signal?: AbortSignal,
  ): Promise<void> {
    const token = getAccessToken()
    const response = await fetch(`${baseURL}/ai/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal,
    })

    if (!response.ok || !response.body) {
      let message = `请求失败 (HTTP ${response.status})`
      try {
        const data = (await response.json()) as { message?: string }
        message = data.message ?? message
      } catch {
        /* 响应不是 JSON，保留默认提示 */
      }
      handlers.onError?.(message)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE 以空行分隔事件
      const events = buffer.split('\n\n')
      buffer = events.pop() ?? ''

      for (const event of events) {
        const line = event.split('\n').find((item) => item.startsWith('data: '))
        if (!line) continue
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') {
          handlers.onDone?.()
          return
        }
        try {
          const data = JSON.parse(raw) as {
            delta?: string
            error?: string
            citations?: Citation[]
          }
          if (data.error) {
            handlers.onError?.(data.error)
            return
          }
          if (data.citations) {
            handlers.onCitations?.(data.citations)
            continue
          }
          if (data.delta) {
            handlers.onDelta(data.delta)
          }
        } catch {
          /* 忽略无法解析的行 */
        }
      }
    }
    handlers.onDone?.()
  },
}
