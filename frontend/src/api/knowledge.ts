import { apiClient } from './client'

import type {
  KBDocument,
  KnowledgeBase,
  KnowledgeBasePayload,
  SearchHit,
  SearchPayload,
} from '@/types/knowledge'
import type { MessageResponse } from '@/types/api'

export const knowledgeApi = {
  listBases() {
    return apiClient.get<KnowledgeBase[]>('/knowledge-bases')
  },

  createBase(payload: KnowledgeBasePayload) {
    return apiClient.post<KnowledgeBase>('/knowledge-bases', payload)
  },

  updateBase(id: number, payload: Partial<KnowledgeBasePayload>) {
    return apiClient.put<KnowledgeBase>(`/knowledge-bases/${id}`, payload)
  },

  deleteBase(id: number) {
    return apiClient.delete<MessageResponse>(`/knowledge-bases/${id}`)
  },

  listDocuments(kbId: number) {
    return apiClient.get<KBDocument[]>(`/knowledge-bases/${kbId}/documents`)
  },

  /** 上传后服务端会同步做解析 + 向量化，大文件耗时较长，单独放宽超时 */
  uploadDocument(kbId: number, file: File) {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<KBDocument>(`/knowledge-bases/${kbId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },

  deleteDocument(kbId: number, documentId: number) {
    return apiClient.delete<MessageResponse>(
      `/knowledge-bases/${kbId}/documents/${documentId}`,
    )
  },

  search(payload: SearchPayload) {
    return apiClient.post<SearchHit[]>('/knowledge-bases/search/query', payload)
  },
}
