<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'

import { resolveErrorMessage } from '@/api/client'
import { departmentsApi, rolesApi } from '@/api/roles'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import type { DepartmentNode } from '@/types/department'
import type { RoleItem } from '@/types/role'
import type { UserCreatePayload, UserItem, UserUpdatePayload } from '@/types/user'

const auth = useAuthStore()

const loading = ref(false)
const rows = ref<UserItem[]>([])
const total = ref(0)
const roles = ref<RoleItem[]>([])
const departments = ref<DepartmentNode[]>([])

const query = reactive({
  keyword: '',
  department_id: undefined as number | undefined,
  status: undefined as number | undefined,
  role_id: undefined as number | undefined,
  page: 1,
  page_size: 10,
})

const dialogVisible = ref(false)
const submitting = ref(false)
const editing = ref<UserItem | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: '',
  real_name: '',
  email: '',
  phone: '',
  department_id: undefined as number | undefined,
  status: 1,
  role_ids: [] as number[],
})

const canCreate = computed(() => auth.has('user:create'))
const canUpdate = computed(() => auth.has('user:update'))
const canDelete = computed(() => auth.has('user:delete'))
const canReadRoles = computed(() => auth.has('role:read'))
const canReadDepartments = computed(() => auth.has('department:read'))

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z][A-Za-z0-9_.-]{2,63}$/, message: '字母开头，3-64 位，可含数字、下划线、点、连字符', trigger: 'blur' },
  ],
  password: [
    {
      validator: (_rule, value: string, callback) => {
        if (editing.value) {
          if (value && value.length < 8) {
            callback(new Error('密码至少 8 位'))
            return
          }
          callback()
          return
        }
        if (!value) {
          callback(new Error('请输入初始密码'))
          return
        }
        if (value.length < 8 || !/[A-Za-z]/.test(value) || !/\d/.test(value)) {
          callback(new Error('至少 8 位，且同时包含字母和数字'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
}

function resetForm(): void {
  form.username = ''
  form.password = ''
  form.real_name = ''
  form.email = ''
  form.phone = ''
  form.department_id = undefined
  form.status = 1
  form.role_ids = []
  formRef.value?.clearValidate()
}

async function loadUsers(): Promise<void> {
  loading.value = true
  try {
    const { data } = await usersApi.list({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      department_id: query.department_id,
      status: query.status,
      role_id: query.role_id,
    })
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '用户列表加载失败'))
  } finally {
    loading.value = false
  }
}

async function loadOptions(): Promise<void> {
  if (canReadRoles.value) {
    try {
      const { data } = await rolesApi.list()
      roles.value = data
    } catch {
      roles.value = []
    }
  }
  if (canReadDepartments.value) {
    try {
      const { data } = await departmentsApi.tree()
      departments.value = data
    } catch {
      departments.value = []
    }
  }
}

function handleSearch(): void {
  query.page = 1
  void loadUsers()
}

function handleReset(): void {
  query.keyword = ''
  query.department_id = undefined
  query.status = undefined
  query.role_id = undefined
  query.page = 1
  void loadUsers()
}

function openCreate(): void {
  editing.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: UserItem): void {
  editing.value = row
  form.username = row.username
  form.password = ''
  form.real_name = row.real_name ?? ''
  form.email = row.email ?? ''
  form.phone = row.phone ?? ''
  form.department_id = row.department_id ?? undefined
  form.status = row.status
  form.role_ids = row.roles.map((role) => role.id)
  dialogVisible.value = true
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    if (editing.value) {
      const payload: UserUpdatePayload = {
        real_name: form.real_name || null,
        email: form.email || null,
        phone: form.phone || null,
        department_id: form.department_id ?? null,
        status: form.status,
        role_ids: form.role_ids,
      }
      if (form.password) {
        payload.password = form.password
      }
      await usersApi.update(editing.value.id, payload)
      ElMessage.success('用户已更新')
    } else {
      const payload: UserCreatePayload = {
        username: form.username,
        password: form.password,
        real_name: form.real_name || null,
        email: form.email || null,
        phone: form.phone || null,
        department_id: form.department_id ?? null,
        status: form.status,
        role_ids: form.role_ids,
      }
      await usersApi.create(payload)
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    await loadUsers()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '保存失败'))
  } finally {
    submitting.value = false
  }
}

async function handleDisable(row: UserItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定要禁用用户「${row.real_name || row.username}」吗？禁用后该账号无法登录。`,
      '禁用用户',
      { type: 'warning', confirmButtonText: '禁用', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await usersApi.disable(row.id)
    ElMessage.success('用户已禁用')
    await loadUsers()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '操作失败'))
  }
}

onMounted(async () => {
  await Promise.all([loadOptions(), loadUsers()])
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="table-toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="用户名 / 姓名 / 邮箱"
          clearable
          style="width: 240px"
          :prefix-icon="Search"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-tree-select
          v-if="canReadDepartments"
          v-model="query.department_id"
          :data="departments"
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          check-strictly
          clearable
          placeholder="所属部门"
          style="width: 180px"
          @change="handleSearch"
        />
        <el-select
          v-if="canReadRoles"
          v-model="query.role_id"
          placeholder="角色"
          clearable
          style="width: 160px"
          @change="handleSearch"
        >
          <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
        </el-select>
        <el-select
          v-model="query.status"
          placeholder="状态"
          clearable
          style="width: 120px"
          @change="handleSearch"
        >
          <el-option label="正常" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        <div class="spacer" />
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          新建用户
        </el-button>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="real_name" label="姓名" min-width="110">
          <template #default="{ row }">{{ row.real_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="department_name" label="部门" min-width="120">
          <template #default="{ row }">{{ row.department_name || '未分配' }}</template>
        </el-table-column>
        <el-table-column label="角色" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="role in row.roles"
              :key="role.id"
              size="small"
              effect="plain"
              class="role-tag"
            >
              {{ role.name }}
            </el-tag>
            <span v-if="!row.roles.length" class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" min-width="160">
          <template #default="{ row }">
            {{ row.last_login_at ? row.last_login_at.replace('T', ' ').slice(0, 19) : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button v-if="canUpdate" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-if="canDelete && row.status === 1"
              link
              type="danger"
              @click="handleDisable(row)"
            >
              禁用
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="loadUsers"
          @size-change="handleSearch"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑用户' : '新建用户'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="Boolean(editing)" placeholder="登录账号" />
        </el-form-item>
        <el-form-item :label="editing ? '重置密码' : '初始密码'" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editing ? '留空表示不修改' : '至少 8 位，含字母和数字'"
          />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="name@example.com" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="可选" />
        </el-form-item>
        <el-form-item label="部门">
          <el-tree-select
            v-model="form.department_id"
            :data="departments"
            node-key="id"
            :props="{ label: 'name', children: 'children' }"
            check-strictly
            clearable
            placeholder="未分配"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select
            v-model="form.role_ids"
            multiple
            filterable
            placeholder="选择角色"
            style="width: 100%"
          >
            <el-option
              v-for="role in roles"
              :key="role.id"
              :label="role.name"
              :value="role.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
          <span class="text-muted" style="margin-left: 8px">关闭后该账号无法登录</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.role-tag {
  margin-right: 6px;
}
</style>
