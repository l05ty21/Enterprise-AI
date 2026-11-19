<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

import { resolveErrorMessage } from '@/api/client'
import { rolesApi } from '@/api/roles'
import { useAuthStore } from '@/stores/auth'
import type { PermissionItem, RoleItem } from '@/types/role'

const auth = useAuthStore()

const loading = ref(false)
const roles = ref<RoleItem[]>([])
const permissions = ref<PermissionItem[]>([])

const dialogVisible = ref(false)
const submitting = ref(false)
const editing = ref<RoleItem | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  code: '',
  description: '',
  permission_ids: [] as number[],
})

const canCreate = computed(() => auth.has('role:create'))
const canUpdate = computed(() => auth.has('role:update'))
const canDelete = computed(() => auth.has('role:delete'))

const rules: FormRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    {
      pattern: /^[a-z][a-z0-9_]{1,63}$/,
      message: '小写字母开头，可含数字和下划线',
      trigger: 'blur',
    },
  ],
}

const permissionGroups = computed(() => {
  const labels: Record<string, string> = {
    menu: '菜单权限',
    button: '操作权限',
    api: '接口权限',
  }
  return Object.entries(labels).map(([type, label]) => ({
    type,
    label,
    items: permissions.value.filter((item) => item.type === type),
  }))
})

async function loadRoles(): Promise<void> {
  loading.value = true
  try {
    const { data } = await rolesApi.list()
    roles.value = data
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '角色列表加载失败'))
  } finally {
    loading.value = false
  }
}

async function loadPermissions(): Promise<void> {
  try {
    const { data } = await rolesApi.permissions()
    permissions.value = data
  } catch {
    permissions.value = []
  }
}

function resetForm(): void {
  form.name = ''
  form.code = ''
  form.description = ''
  form.permission_ids = []
  formRef.value?.clearValidate()
}

function openCreate(): void {
  editing.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: RoleItem): void {
  editing.value = row
  form.name = row.name
  form.code = row.code
  form.description = row.description ?? ''
  form.permission_ids = [...row.permission_ids]
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
      await rolesApi.update(editing.value.id, {
        name: form.name,
        description: form.description || null,
        permission_ids: form.permission_ids,
      })
      ElMessage.success('角色已更新')
    } else {
      await rolesApi.create({
        name: form.name,
        code: form.code,
        description: form.description || null,
        permission_ids: form.permission_ids,
      })
      ElMessage.success('角色已创建')
    }
    dialogVisible.value = false
    await loadRoles()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '保存失败'))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: RoleItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定要删除角色「${row.name}」吗？该操作不可恢复。`,
      '删除角色',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await rolesApi.remove(row.id)
    ElMessage.success('角色已删除')
    await loadRoles()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '删除失败'))
  }
}

function permissionNames(ids: number[]): string {
  const names = permissions.value
    .filter((item) => ids.includes(item.id))
    .map((item) => item.name)
  if (names.length <= 3) {
    return names.join('、')
  }
  return `${names.slice(0, 3).join('、')} 等 ${names.length} 项`
}

onMounted(async () => {
  await Promise.all([loadRoles(), loadPermissions()])
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="table-toolbar">
        <span class="text-muted">角色决定用户能看到哪些菜单、能调用哪些接口。</span>
        <div class="spacer" />
        <el-button :icon="Refresh" @click="loadRoles">刷新</el-button>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          新建角色
        </el-button>
      </div>

      <el-table v-loading="loading" :data="roles" border stripe>
        <el-table-column prop="name" label="角色名称" min-width="140" />
        <el-table-column prop="code" label="角色编码" min-width="140">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="权限" min-width="240">
          <template #default="{ row }">
            <span class="text-muted">{{ permissionNames(row.permission_ids) || '未分配' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_count" label="用户数" width="90" align="center" />
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button v-if="canUpdate" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-if="canDelete && row.code !== 'super_admin'"
              link
              type="danger"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑角色' : '新建角色'"
      width="640px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="form.name" placeholder="例如 部门经理" />
        </el-form-item>
        <el-form-item label="角色编码" prop="code">
          <el-input v-model="form.code" :disabled="Boolean(editing)" placeholder="例如 dept_manager" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="权限分配">
          <div class="permission-box">
            <div v-for="group in permissionGroups" :key="group.type" class="permission-group">
              <div class="permission-title">{{ group.label }}</div>
              <el-checkbox-group v-model="form.permission_ids">
                <el-checkbox
                  v-for="item in group.items"
                  :key="item.id"
                  :value="item.id"
                  class="permission-item"
                >
                  {{ item.name }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
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
.permission-box {
  width: 100%;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px 16px;
}

.permission-group + .permission-group {
  margin-top: 12px;
}

.permission-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}

.permission-item {
  width: 160px;
  margin-right: 0;
}
</style>
