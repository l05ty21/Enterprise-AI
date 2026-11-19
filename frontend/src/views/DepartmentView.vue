<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

import { resolveErrorMessage } from '@/api/client'
import { departmentsApi } from '@/api/roles'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import type { DepartmentNode } from '@/types/department'
import type { UserItem } from '@/types/user'

const auth = useAuthStore()

const loading = ref(false)
const tree = ref<DepartmentNode[]>([])
const users = ref<UserItem[]>([])

const dialogVisible = ref(false)
const submitting = ref(false)
const editing = ref<DepartmentNode | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  parent_id: undefined as number | undefined,
  leader_id: undefined as number | undefined,
})

const canCreate = computed(() => auth.has('department:create'))
const canUpdate = computed(() => auth.has('department:update'))
const canDelete = computed(() => auth.has('department:delete'))
const canReadUsers = computed(() => auth.has('user:read'))

const rules: FormRules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }],
}

async function loadTree(): Promise<void> {
  loading.value = true
  try {
    const { data } = await departmentsApi.tree()
    tree.value = data
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '部门树加载失败'))
  } finally {
    loading.value = false
  }
}

async function loadUsers(): Promise<void> {
  if (!canReadUsers.value) {
    return
  }
  try {
    const { data } = await usersApi.list({ page: 1, page_size: 200, status: 1 })
    users.value = data.items
  } catch {
    users.value = []
  }
}

function resetForm(): void {
  form.name = ''
  form.parent_id = undefined
  form.leader_id = undefined
  formRef.value?.clearValidate()
}

function openCreate(parent?: DepartmentNode): void {
  editing.value = null
  resetForm()
  form.parent_id = parent?.id
  dialogVisible.value = true
}

function openEdit(row: DepartmentNode): void {
  editing.value = row
  form.name = row.name
  form.parent_id = row.parent_id ?? undefined
  form.leader_id = row.leader_id ?? undefined
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
      await departmentsApi.update(editing.value.id, {
        name: form.name,
        parent_id: form.parent_id ?? null,
        leader_id: form.leader_id ?? null,
      })
      ElMessage.success('部门已更新')
    } else {
      await departmentsApi.create({
        name: form.name,
        parent_id: form.parent_id ?? null,
        leader_id: form.leader_id ?? null,
      })
      ElMessage.success('部门已创建')
    }
    dialogVisible.value = false
    await loadTree()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '保存失败'))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: DepartmentNode): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定要删除部门「${row.name}」吗？请先确保没有子部门和成员。`,
      '删除部门',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await departmentsApi.remove(row.id)
    ElMessage.success('部门已删除')
    await loadTree()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '删除失败'))
  }
}

onMounted(async () => {
  await Promise.all([loadTree(), loadUsers()])
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="table-toolbar">
        <span class="text-muted">部门支持多级树形结构，可用于数据权限和审批流。</span>
        <div class="spacer" />
        <el-button :icon="Refresh" @click="loadTree">刷新</el-button>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate()">
          新建部门
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="tree"
        row-key="id"
        border
        default-expand-all
        :tree-props="{ children: 'children' }"
      >
        <el-table-column prop="name" label="部门名称" min-width="220" />
        <el-table-column prop="leader_name" label="负责人" min-width="120">
          <template #default="{ row }">{{ row.leader_name || '未指定' }}</template>
        </el-table-column>
        <el-table-column prop="member_count" label="成员数" width="100" align="center" />
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">
            {{ row.created_at ? row.created_at.replace('T', ' ').slice(0, 19) : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button v-if="canCreate" link type="primary" @click="openCreate(row)">
              添加子部门
            </el-button>
            <el-button v-if="canUpdate" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="canDelete" link type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑部门' : '新建部门'"
      width="520px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="form.name" placeholder="例如 前端组" />
        </el-form-item>
        <el-form-item label="上级部门">
          <el-tree-select
            v-model="form.parent_id"
            :data="tree"
            node-key="id"
            :props="{ label: 'name', children: 'children' }"
            check-strictly
            clearable
            placeholder="不选则为顶级部门"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="canReadUsers" label="负责人">
          <el-select
            v-model="form.leader_id"
            filterable
            clearable
            placeholder="可选"
            style="width: 100%"
          >
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.real_name || user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
