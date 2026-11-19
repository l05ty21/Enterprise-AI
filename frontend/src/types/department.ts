export interface DepartmentNode {
  id: number
  organization_id: number
  parent_id: number | null
  name: string
  leader_id: number | null
  leader_name: string | null
  member_count: number
  created_at: string | null
  children: DepartmentNode[]
}

export interface DepartmentPayload {
  name?: string
  parent_id?: number | null
  leader_id?: number | null
}
