<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'

import { resolveErrorMessage } from '@/api/client'
import { ticketsApi } from '@/api/tickets'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import type { Ticket, TicketDetail, TicketPriority, TicketStatus } from '@/types/ticket'

const auth = useAuthStore()
const canCreate = computed(() => auth.has('ticket:create'))
const canHandle = computed(() => auth.has('ticket:update'))
const canReadUsers = computed(() => auth.has('user:read'))

const loading = ref(false)
const rows = ref<Ticket[]>([])
const total = ref(0)

const query = reactive({
  keyword: '',
  status: '' as TicketStatus | '',
  priority: '' as TicketPriority | '',
  mine: false,
  page: 1,
  page_size: 10,
})

const PRIORITY_TEXT: Record<string, string> = { low: '低', medium: '中', high: '高', urgent: '紧急' }
const PRIORITY_TYPE: Record<string, 'info' | 'primary' | 'warning' | 'danger'> = {
  low: 'info',
  medium: 'primary',
  high: 'warning',
  urgent: 'danger',
}
const STATUS_TEXT: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  closed: '已关闭',
}
const STATUS_TYPE: Record<string, 'info' | 'primary' | 'success' | 'warning'> = {
  pending: 'warning',
  processing: 'primary',
  resolved: 'success',
  closed: 'info',
}

async function loadTickets(): Promise<void> {
  loading.value = true
  try {
    const { data } = await ticketsApi.list({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status || undefined,
      priority: query.priority || undefined,
      mine: query.mine,
    })
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '工单列表加载失败'))
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void loadTickets()
}

function handleReset(): void {
  query.keyword = ''
  query.status = ''
  query.priority = ''
  query.mine = false
  query.page = 1
  void loadTickets()
}

// ---------------------------------------------------------------- 新建
const createVisible = ref(false)
const submitting = ref(false)
const form = reactive({ title: '', description: '', priority: 'medium' as TicketPriority })

function openCreate(): void {
  form.title = ''
  form.description = ''
  form.priority = 'medium'
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (!form.title.trim()) {
    ElMessage.warning('请填写工单标题')
    return
  }
  submitting.value = true
  try {
    await ticketsApi.create({
      title: form.title.trim(),
      description: form.description.trim() || null,
      priority: form.priority,
    })
    ElMessage.success('工单已提交')
    createVisible.value = false
    await loadTickets()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '提交失败'))
  } finally {
    submitting.value = false
  }
}

// ---------------------------------------------------------------- 详情
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<TicketDetail | null>(null)
const assigneeId = ref<number | null>(null)
const users = ref<{ id: number; real_name: string | null; username: string }[]>([])
const commentText = ref('')
const acting = ref(false)

async function ensureUsers(): Promise<void> {
  if (!canReadUsers.value || users.value.length) return
  try {
    const { data } = await usersApi.list({ page: 1, page_size: 100 })
    users.value = data.items.map((u) => ({ id: u.id, real_name: u.real_name, username: u.username }))
  } catch {
    // 没有用户读权限就不显示指派下拉
  }
}

async function openDetail(row: Ticket): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const { data } = await ticketsApi.detail(row.id)
    detail.value = data
    assigneeId.value = data.assignee_id
    commentText.value = ''
    void ensureUsers()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '工单详情加载失败'))
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function refreshDetail(): Promise<void> {
  if (!detail.value) return
  const { data } = await ticketsApi.detail(detail.value.id)
  detail.value = data
  assigneeId.value = data.assignee_id
}

async function changeStatus(status: TicketStatus, remark?: string): Promise<void> {
  if (!detail.value) return
  acting.value = true
  try {
    await ticketsApi.update(detail.value.id, { status, remark: remark || null })
    ElMessage.success('已更新')
    await Promise.all([refreshDetail(), loadTickets()])
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '更新失败'))
  } finally {
    acting.value = false
  }
}

async function assignTo(): Promise<void> {
  if (!detail.value || !assigneeId.value) return
  acting.value = true
  try {
    await ticketsApi.update(detail.value.id, { assignee_id: assigneeId.value })
    ElMessage.success('已指派')
    await Promise.all([refreshDetail(), loadTickets()])
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '指派失败'))
  } finally {
    acting.value = false
  }
}

async function sendComment(): Promise<void> {
  if (!detail.value || !commentText.value.trim()) return
  acting.value = true
  try {
    await ticketsApi.addComment(detail.value.id, commentText.value.trim())
    commentText.value = ''
    await refreshDetail()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error, '评论发送失败'))
  } finally {
    acting.value = false
  }
}

onMounted(loadTickets)
</script>

<template>
  <div>
    <el-card shadow="never">
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="编号 / 标题"
          clearable
          style="width: 220px"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 130px">
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已解决" value="resolved" />
          <el-option label="已关闭" value="closed" />
        </el-select>
        <el-select v-model="query.priority" placeholder="优先级" clearable style="width: 130px">
          <el-option label="低" value="low" />
          <el-option label="中" value="medium" />
          <el-option label="高" value="high" />
          <el-option label="紧急" value="urgent" />
        </el-select>
        <el-checkbox v-model="query.mine" @change="handleSearch">只看我的</el-checkbox>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <div class="spacer" />
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          新建工单
        </el-button>
      </div>

      <el-table :data="rows" v-loading="loading" style="width: 100%" @row-dblclick="openDetail">
        <el-table-column prop="ticket_no" label="编号" width="150" />
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column label="优先级" width="90">
          <template #default="{ row }">
            <el-tag :type="PRIORITY_TYPE[row.priority]" size="small">
              {{ PRIORITY_TEXT[row.priority] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="STATUS_TYPE[row.status]" size="small">
              {{ STATUS_TEXT[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="110" />
        <el-table-column label="处理人" width="110">
          <template #default="{ row }">{{ row.assignee_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
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
          @current-change="loadTickets"
          @size-change="handleSearch"
        />
      </div>
    </el-card>

    <el-dialog v-model="createVisible" title="新建工单" width="520px">
      <el-form label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="255" placeholder="一句话说明问题" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="5"
            maxlength="5000"
            show-word-limit
            placeholder="补充现象、影响范围、期望结果"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="工单详情" size="46%">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <h3 class="ticket-title">{{ detail.title }}</h3>
          <div class="meta">
            <el-tag :type="STATUS_TYPE[detail.status]" size="small">
              {{ STATUS_TEXT[detail.status] }}
            </el-tag>
            <el-tag :type="PRIORITY_TYPE[detail.priority]" size="small">
              {{ PRIORITY_TEXT[detail.priority] }}
            </el-tag>
            <span class="muted">{{ detail.ticket_no }}</span>
            <span class="muted">{{ detail.creator_name }} 创建于 {{ detail.created_at }}</span>
          </div>

          <p class="desc">{{ detail.description || '（没有填写描述）' }}</p>

          <div v-if="canHandle" class="actions">
            <el-select
              v-if="canReadUsers"
              v-model="assigneeId"
              placeholder="选择处理人"
              style="width: 180px"
            >
              <el-option
                v-for="u in users"
                :key="u.id"
                :label="u.real_name || u.username"
                :value="u.id"
              />
            </el-select>
            <el-button v-if="canReadUsers" :loading="acting" @click="assignTo">指派</el-button>
            <el-button
              v-if="detail.status === 'pending'"
              type="primary"
              :loading="acting"
              @click="changeStatus('processing')"
            >
              开始处理
            </el-button>
            <el-button
              v-if="detail.status === 'processing'"
              type="success"
              :loading="acting"
              @click="changeStatus('resolved')"
            >
              标记已解决
            </el-button>
            <el-button
              v-if="detail.status !== 'closed'"
              :loading="acting"
              @click="changeStatus('closed')"
            >
              关闭
            </el-button>
          </div>

          <el-divider content-position="left">流转记录</el-divider>
          <el-timeline>
            <el-timeline-item
              v-for="h in detail.histories"
              :key="h.id"
              :timestamp="h.created_at"
              placement="top"
            >
              {{ h.operator_name }}：{{ h.old_status ? STATUS_TEXT[h.old_status] + ' → ' : '' }}{{
                STATUS_TEXT[h.new_status || ''] || h.new_status
              }}
              <span v-if="h.remark" class="muted">（{{ h.remark }}）</span>
            </el-timeline-item>
          </el-timeline>

          <el-divider content-position="left">评论（{{ detail.comments.length }}）</el-divider>
          <div v-for="c in detail.comments" :key="c.id" class="comment">
            <div class="comment-head">
              <strong>{{ c.user_name }}</strong>
              <span class="muted">{{ c.created_at }}</span>
            </div>
            <div>{{ c.content }}</div>
          </div>
          <el-empty v-if="!detail.comments.length" description="还没有评论" :image-size="60" />

          <div class="comment-box">
            <el-input
              v-model="commentText"
              type="textarea"
              :rows="3"
              maxlength="2000"
              placeholder="补充说明或追问"
            />
            <el-button
              type="primary"
              :loading="acting"
              :disabled="!commentText.trim()"
              @click="sendComment"
            >
              发送
            </el-button>
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
  flex-wrap: wrap;
}
.spacer {
  flex: 1;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
.ticket-title {
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
.desc {
  white-space: pre-wrap;
  color: #303133;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  margin: 12px 0;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 12px 0;
}
.comment {
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
}
.comment-head {
  display: flex;
  gap: 10px;
  align-items: baseline;
  margin-bottom: 4px;
}
.comment-box {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}
</style>
