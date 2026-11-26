<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { ArrowDown, ArrowUp, Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'

import { approvalsApi } from '@/api/approvals'
import { attachmentsApi } from '@/api/attachments'
import { resolveErrorMessage } from '@/api/client'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import type { Approval, ApprovalDetail, BusinessType } from '@/types/approval'

const auth = useAuthStore()
const route = useRoute()
const canCreate = computed(() => auth.has('approval:create'))
const canApprove = computed(() => auth.has('approval:approve'))
const canReadUsers = computed(() => auth.has('user:read'))

const scope = ref<'mine' | 'todo' | 'all'>('mine')
const loading = ref(false)
const rows = ref<Approval[]>([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10 })
const uploading = ref(false)

const STATUS_TEXT: Record<string, string> = {
  pending: '审批中',
  approved: '已通过',
  rejected: '已驳回',
  waiting: '等待中',
}
const STATUS_TYPE: Record<string, 'warning' | 'success' | 'danger' | 'info'> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  waiting: 'info',
}
const TYPE_TEXT: Record<string, string> = {
  expense: '报销',
  leave: '请假',
  purchase: '采购',
  other: '其他',
}

async function loadApprovals(): Promise<void> {
  loading.value = true
  try {
    const { data } = await approvalsApi.list({
      page: query.page,
      page_size: query.page_size,
      scope: scope.value,
    })
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '审批列表加载失败'))
  } finally {
    loading.value = false
  }
}

function switchScope(value: string): void {
  scope.value = value as 'mine' | 'todo' | 'all'
  query.page = 1
  void loadApprovals()
}

const createVisible = ref(false)
const submitting = ref(false)
const users = ref<{ id: number; real_name: string | null; username: string }[]>([])
const selectedApprovers = ref<number[]>([])
const form = reactive({
  title: '',
  business_type: 'expense' as BusinessType,
  amount: undefined as number | undefined,
  reason: '',
})

async function ensureUsers(): Promise<void> {
  if (!canReadUsers.value || users.value.length) return
  try {
    const { data } = await usersApi.list({ page: 1, page_size: 100 })
    users.value = data.items
      .filter((u) => u.id !== auth.user?.id && u.status === 1)
      .map((u) => ({ id: u.id, real_name: u.real_name, username: u.username }))
  } catch {
    // 无用户读权限时只能走自动解析审批人
  }
}

function openCreate(): void {
  form.title = ''
  form.business_type = 'expense'
  form.amount = undefined
  form.reason = ''
  selectedApprovers.value = []
  createVisible.value = true
  void ensureUsers()
}

function userLabel(id: number): string {
  const user = users.value.find((item) => item.id === id)
  return user ? user.real_name || user.username : String(id)
}

function moveApprover(index: number, delta: number): void {
  const target = index + delta
  if (target < 0 || target >= selectedApprovers.value.length) return
  const next = [...selectedApprovers.value]
  const tmp = next[index]
  next[index] = next[target]
  next[target] = tmp
  selectedApprovers.value = next
}

async function submitCreate(): Promise<void> {
  if (!form.title.trim()) {
    ElMessage.warning('请填写审批标题')
    return
  }
  submitting.value = true
  try {
    await approvalsApi.create({
      title: form.title.trim(),
      business_type: form.business_type,
      amount: form.amount ?? null,
      reason: form.reason.trim() || null,
      approver_ids: selectedApprovers.value.length ? [...selectedApprovers.value] : undefined,
    })
    ElMessage.success('已提交审批')
    createVisible.value = false
    scope.value = 'mine'
    await loadApprovals()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '提交失败'))
  } finally {
    submitting.value = false
  }
}

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<ApprovalDetail | null>(null)
const decisionComment = ref('')
const acting = ref(false)

async function openDetail(row: Approval): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  decisionComment.value = ''
  try {
    const { data } = await approvalsApi.detail(row.id)
    detail.value = data
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '审批详情加载失败'))
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function refreshDetail(): Promise<void> {
  if (!detail.value) return
  const { data } = await approvalsApi.detail(detail.value.id)
  detail.value = data
}

async function decide(action: 'approve' | 'reject'): Promise<void> {
  if (!detail.value) return
  acting.value = true
  try {
    const { data } = await approvalsApi.decide(detail.value.id, action, decisionComment.value)
    detail.value = data
    decisionComment.value = ''
    ElMessage.success(action === 'approve' ? '已通过' : '已驳回')
    await loadApprovals()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '操作失败'))
  } finally {
    acting.value = false
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function uploadAttachment(options: UploadRequestOptions): Promise<void> {
  if (!detail.value) return
  uploading.value = true
  try {
    await attachmentsApi.uploadApproval(detail.value.id, options.file as File)
    ElMessage.success('附件已上传')
    await refreshDetail()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '附件上传失败'))
  } finally {
    uploading.value = false
  }
}

async function downloadAttachment(id: number, filename: string): Promise<void> {
  try {
    await attachmentsApi.download(id, filename)
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '下载失败'))
  }
}

async function removeAttachment(id: number): Promise<void> {
  try {
    await attachmentsApi.remove(id)
    ElMessage.success('附件已删除')
    await refreshDetail()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '删除失败'))
  }
}

function taskStatusText(status: string): string {
  return STATUS_TEXT[status] || status
}

onMounted(() => {
  if (route.query.scope === 'todo') {
    scope.value = 'todo'
  }
  void loadApprovals()
})
</script>

<template>
  <div>
    <el-card shadow="never">
      <div class="toolbar">
        <el-radio-group :model-value="scope" @change="switchScope">
          <el-radio-button value="mine">我发起的</el-radio-button>
          <el-radio-button value="todo">待我审批</el-radio-button>
          <el-radio-button v-if="canApprove" value="all">全部</el-radio-button>
        </el-radio-group>
        <el-button :icon="Refresh" @click="loadApprovals">刷新</el-button>
        <div class="spacer" />
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          发起审批
        </el-button>
      </div>

      <el-table :data="rows" v-loading="loading" style="width: 100%" @row-dblclick="openDetail">
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">{{ TYPE_TEXT[row.business_type] || row.business_type }}</template>
        </el-table-column>
        <el-table-column label="金额" width="110">
          <template #default="{ row }">
            {{ row.amount === null || row.amount === undefined ? '—' : `¥ ${row.amount}` }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="STATUS_TYPE[row.status]" size="small">{{ STATUS_TEXT[row.status] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applicant_name" label="申请人" width="110" />
        <el-table-column label="当前节点" width="90">
          <template #default="{ row }">第 {{ row.current_node || 1 }} 级</template>
        </el-table-column>
        <el-table-column label="审批人" width="120">
          <template #default="{ row }">{{ row.current_approver_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button v-if="row.can_decide" link type="success" @click="openDetail(row)">
              去审批
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadApprovals"
          @size-change="loadApprovals"
        />
      </div>
    </el-card>

    <el-dialog v-model="createVisible" title="发起审批" width="600px">
      <el-form label-width="86px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" placeholder="例如：上海出差报销 800 元" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.business_type" style="width: 100%">
            <el-option label="报销" value="expense" />
            <el-option label="请假" value="leave" />
            <el-option label="采购" value="purchase" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number
            v-model="form.amount"
            :min="0"
            :max="99999999"
            :precision="2"
            controls-position="right"
            style="width: 100%"
            placeholder="非报销类可留空"
          />
        </el-form-item>
        <el-form-item label="审批人">
          <div class="approver-box">
            <el-select
              v-if="canReadUsers"
              v-model="selectedApprovers"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="按顺序选择 1～N 位审批人；不选则自动分配"
              style="width: 100%"
            >
              <el-option
                v-for="u in users"
                :key="u.id"
                :label="u.real_name || u.username"
                :value="u.id"
              />
            </el-select>
            <p v-else class="hint">无用户列表权限时将自动解析审批人</p>
            <div v-if="selectedApprovers.length" class="ordered-list">
              <div v-for="(id, index) in selectedApprovers" :key="id" class="ordered-item">
                <span>第 {{ index + 1 }} 级 · {{ userLabel(id) }}</span>
                <span>
                  <el-button
                    link
                    :icon="ArrowUp"
                    :disabled="index === 0"
                    @click="moveApprover(index, -1)"
                  />
                  <el-button
                    link
                    :icon="ArrowDown"
                    :disabled="index === selectedApprovers.length - 1"
                    @click="moveApprover(index, 1)"
                  />
                </span>
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="说明">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="补充事由、时间等；提交后可在详情中上传附件"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="审批详情" size="44%">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <h3 class="title">{{ detail.title }}</h3>
          <div class="meta">
            <el-tag :type="STATUS_TYPE[detail.status]" size="small">
              {{ STATUS_TEXT[detail.status] }}
            </el-tag>
            <span class="muted">{{ TYPE_TEXT[detail.business_type] || detail.business_type }}</span>
            <span v-if="detail.amount !== null" class="amount">¥ {{ detail.amount }}</span>
            <span class="muted">第 {{ detail.current_node || 1 }} 级</span>
            <span class="muted">{{ detail.applicant_name }} 提交于 {{ detail.created_at }}</span>
          </div>

          <p class="reason">{{ detail.reason || '（没有填写说明）' }}</p>

          <el-divider content-position="left">
            附件（{{ detail.attachments?.length || 0 }}）
          </el-divider>
          <div class="attach-list">
            <div v-for="file in detail.attachments || []" :key="file.id" class="attach-item">
              <div>
                <el-button link type="primary" @click="downloadAttachment(file.id, file.filename)">
                  {{ file.filename }}
                </el-button>
                <span class="muted">
                  {{ formatSize(file.file_size) }} · {{ file.uploader_name || '未知' }}
                </span>
              </div>
              <el-button link type="danger" @click="removeAttachment(file.id)">删除</el-button>
            </div>
            <el-empty
              v-if="!(detail.attachments && detail.attachments.length)"
              description="暂无附件"
              :image-size="48"
            />
          </div>
          <el-upload
            :http-request="uploadAttachment"
            :show-file-list="false"
            :disabled="uploading"
          >
            <el-button :icon="UploadFilled" :loading="uploading">上传附件</el-button>
          </el-upload>

          <el-divider content-position="left">审批流程</el-divider>
          <el-timeline>
            <el-timeline-item
              v-for="t in detail.tasks"
              :key="t.id"
              :timestamp="t.handled_at || (t.status === 'waiting' ? '排队中' : '等待处理')"
              :type="
                t.status === 'approved'
                  ? 'success'
                  : t.status === 'rejected'
                    ? 'danger'
                    : t.status === 'waiting'
                      ? 'info'
                      : 'primary'
              "
            >
              <strong>第 {{ t.node_index || 1 }} 级 · {{ t.approver_name }}</strong>
              <span class="muted"> · {{ taskStatusText(t.status) }}</span>
              <div v-if="t.comment" class="muted">意见：{{ t.comment }}</div>
            </el-timeline-item>
          </el-timeline>

          <div v-if="detail.can_decide" class="decision">
            <el-input
              v-model="decisionComment"
              type="textarea"
              :rows="3"
              maxlength="500"
              placeholder="审批意见（可选）"
            />
            <div class="decision-actions">
              <el-button type="danger" plain :loading="acting" @click="decide('reject')">
                驳回
              </el-button>
              <el-button type="success" :loading="acting" @click="decide('approve')">
                通过
              </el-button>
            </div>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.spacer {
  flex: 1;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
.title {
  margin: 0 0 8px;
  font-size: 18px;
}
.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.muted {
  color: #909399;
  font-size: 12px;
}
.amount {
  color: #e6a23c;
  font-weight: 600;
}
.reason {
  white-space: pre-wrap;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  margin: 12px 0;
}
.decision {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.decision-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.approver-box {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.hint {
  margin: 0;
  color: #909399;
  font-size: 12px;
}
.ordered-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ordered-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
}
.attach-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.attach-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
  background: #f8fafc;
  border-radius: 6px;
}
</style>
