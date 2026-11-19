import type { PageQuery } from './api'

export interface RoleBrief {
  id: number
  name: string
  code: string
}

export interface CurrentUser {
  id: number
  username: string
  real_name: string | null
  email: string | null
  phone: string | null
  avatar: string | null
  organization_id: number
  organization_name: string | null
  department_id: number | null
  department_name: string | null
  is_superuser: boolean
  roles: RoleBrief[]
  permissions: string[]
}

export interface LoginPayload {
  username: string
  password: string
  organization_code?: string
}

export interface RegisterPayload {
  organization_name: string
  organization_code: string
  username: string
  password: string
  real_name?: string | null
  email?: string | null
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserItem {
  id: number
  organization_id: number
  department_id: number | null
  department_name: string | null
  username: string
  real_name: string | null
  email: string | null
  phone: string | null
  avatar: string | null
  status: number
  roles: RoleBrief[]
  last_login_at: string | null
  created_at: string | null
}

export interface UserQuery extends PageQuery {
  keyword?: string
  department_id?: number
  status?: number
  role_id?: number
}

export interface UserCreatePayload {
  username: string
  password: string
  real_name?: string | null
  email?: string | null
  phone?: string | null
  department_id?: number | null
  status?: number
  role_ids?: number[]
}

export type UserUpdatePayload = Partial<Omit<UserCreatePayload, 'username'>> & {
  role_ids?: number[]
}

export interface ProfilePayload {
  real_name?: string | null
  email?: string | null
  phone?: string | null
  avatar?: string | null
}

export interface PasswordPayload {
  old_password: string
  new_password: string
}
