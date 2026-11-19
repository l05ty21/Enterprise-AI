import { apiClient } from './client'

import type { DepartmentNode, DepartmentPayload } from '@/types/department'
import type { MessageResponse } from '@/types/api'
import type {
  PermissionItem,
  RoleCreatePayload,
  RoleItem,
  RoleUpdatePayload,
} from '@/types/role'

export const rolesApi = {
  list() {
    return apiClient.get<RoleItem[]>('/roles')
  },

  detail(id: number) {
    return apiClient.get<RoleItem>(`/roles/${id}`)
  },

  create(payload: RoleCreatePayload) {
    return apiClient.post<RoleItem>('/roles', payload)
  },

  update(id: number, payload: RoleUpdatePayload) {
    return apiClient.put<RoleItem>(`/roles/${id}`, payload)
  },

  remove(id: number) {
    return apiClient.delete<MessageResponse>(`/roles/${id}`)
  },

  permissions() {
    return apiClient.get<PermissionItem[]>('/permissions')
  },
}

export const departmentsApi = {
  tree() {
    return apiClient.get<DepartmentNode[]>('/departments')
  },

  create(payload: DepartmentPayload) {
    return apiClient.post<DepartmentNode>('/departments', payload)
  },

  update(id: number, payload: DepartmentPayload) {
    return apiClient.put<DepartmentNode>(`/departments/${id}`, payload)
  },

  remove(id: number) {
    return apiClient.delete<MessageResponse>(`/departments/${id}`)
  },
}
