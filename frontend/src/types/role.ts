export interface PermissionItem {
  id: number
  name: string
  code: string
  type: string
  parent_id: number | null
  path: string | null
  method: string | null
}

export interface RoleItem {
  id: number
  organization_id: number
  name: string
  code: string
  description: string | null
  permission_ids: number[]
  user_count: number
  created_at: string | null
}

export interface RoleCreatePayload {
  name: string
  code: string
  description?: string | null
  permission_ids?: number[]
}

export interface RoleUpdatePayload {
  name?: string
  description?: string | null
  permission_ids?: number[]
}
