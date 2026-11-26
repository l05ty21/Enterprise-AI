<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  Checked,
  Document,
  Files,
  Plus,
  Tickets,
} from '@element-plus/icons-vue'

import { approvalsApi } from '@/api/approvals'
import { resolveErrorMessage } from '@/api/client'
import { ticketsApi } from '@/api/tickets'
import { useAuthStore } from '@/stores/auth'
import type { Approval } from '@/types/approval'
import type { Ticket } from '@/types/ticket'

const auth = useAuthStore()
const router = useRouter()

const loading = reactive({
  tickets: false,
  approvals: false,
  mineOpen: false,
})

const todoTickets = ref<Ticket[]>([])
const todoApprovals = ref<Approval[]>([])
const mineOpenTotal = ref(0)
const ticketTodoTotal = ref(0)
const approvalTodoTotal = ref(0)

const PRIORITY_TEXT: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  urgent: '紧急',
}
const STATUS_TEXT: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  resolved: '已解决',
  closed: '已关闭',
}
const APPROVAL_STATUS: Record<string, string> = {
  pending: '审批中',
  approved: '已通过',
  rejected: '已驳回',
}

const canTicket = computed(() => auth.has('ticket:read'))
const canApproval = computed(() => auth.has('approval:read'))
const canCreateTicket = computed(() => auth.has('ticket:create'))
const canCreateApproval = computed(() => auth.has('approval:create'))
const canAi = computed(() => auth.has('ai:chat'))
const canKnowledge = computed(() => auth.has('knowledge:read'))

async function loadTodoTickets(): Promise<void> {
  if (!canTicket.value) return
  loading.tickets = true
  try {
    const { data } = await ticketsApi.list({
      page: 1,
      page_size: 8,
      assignee_me: true,
    })
    todoTickets.value = data.items
    ticketTodoTotal.value = data.total
  } catch (error) {
    ElMessage.warning(resolveErrorMessage(error, '待办工单加载失败'))
  } finally {
    loading.tickets = false
  }
}

async function loadTodoApprovals(): Promise<void> {
  if (!canApproval.value) return
  loading.approvals = true
  try {
    const { data } = await approvalsApi.list({
      page: 1,
      page_size: 8,
      scope: 'todo',
    })
    todoApprovals.value = data.items
    approvalTodoTotal.value = data.total
  } catch (error) {
    ElMessage.warning(resolveErrorMessage(error, '待办审批加载失败'))
  } finally {
    loading.approvals = false
  }
}

async function loadMineOpen(): Promise<void> {
  if (!canTicket.value) return
  loading.mineOpen = true
  try {
    // 分别取 pending/processing/resolved 会多次请求；用 mine + 前端汇总 total 不够准
    // 这里用三次轻量请求拿总数（各 page_size=1）
    const statuses = ['pending', 'processing', 'resolved'] as const
    const results = await Promise.all(
      statuses.map((status) =>
        ticketsApi.list({ page: 1, page_size: 1, mine: true, status }),
      ),
    )
    mineOpenTotal.value = results.reduce((sum, r) => sum + r.data.total, 0)
  } catch {
    mineOpenTotal.value = 0
  } finally {
    loading.mineOpen = false
  }
}

function goTickets(assigneeMe = false): void {
  void router.push({ path: '/tickets', query: assigneeMe ? { assignee_me: '1' } : {} })
}

function goApprovals(todo = false): void {
  void router.push({ path: '/approvals', query: todo ? { scope: 'todo' } : {} })
}

onMounted(() => {
  void Promise.all([loadTodoTickets(), loadTodoApprovals(), loadMineOpen()])
})
</script>

<template>
  <div>
    <el-card shadow="never" class="welcome-card">
      <div class="welcome">
        <div>
          <h2>你好，{{ auth.displayName }}</h2>
          <p class="text-muted">
            当前企业：{{ auth.user?.organization_name ?? '-' }} ·
            部门：{{ auth.user?.department_name ?? '未分配' }} ·
            角色：{{ auth.roles.map((role) => role.name).join('、') || '无' }}
          </p>
        </div>
        <el-tag v-if="auth.isSuperuser" type="danger" effect="dark" size="large">
          超级管理员
        </el-tag>
      </div>
    </el-card>

    <el-row :gutter="16" class="stat-row">
      <el-col :xs="24" :sm="8">
        <el-card
          shadow="hover"
          class="stat-card clickable"
          v-loading="loading.tickets"
          @click="goTickets(true)"
        >
          <div class="stat-label">待我处理工单</div>
          <div class="stat-value">{{ canTicket ? ticketTodoTotal : '—' }}</div>
          <div class="stat-hint">指派给我且未关闭</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card
          shadow="hover"
          class="stat-card clickable"
          v-loading="loading.approvals"
          @click="goApprovals(true)"
        >
          <div class="stat-label">待我审批</div>
          <div class="stat-value">{{ canApproval ? approvalTodoTotal : '—' }}</div>
          <div class="stat-hint">当前节点轮到你</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card
          shadow="hover"
          class="stat-card clickable"
          v-loading="loading.mineOpen"
          @click="goTickets(false)"
        >
          <div class="stat-label">我发起的进行中</div>
          <div class="stat-value">{{ canTicket ? mineOpenTotal : '—' }}</div>
          <div class="stat-hint">我提交或相关的未关闭工单</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="list-card" v-loading="loading.tickets">
          <template #header>
            <div class="card-head">
              <span>待处理工单</span>
              <el-button
                v-if="canTicket"
                link
                type="primary"
                @click="goTickets(true)"
              >
                查看全部
              </el-button>
            </div>
          </template>
          <el-empty
            v-if="!canTicket"
            description="无工单查看权限"
            :image-size="72"
          />
          <el-empty
            v-else-if="!todoTickets.length"
            description="暂无待办工单"
            :image-size="72"
          />
          <div v-else class="todo-list">
            <div
              v-for="item in todoTickets"
              :key="item.id"
              class="todo-item"
              @click="goTickets(true)"
            >
              <div class="todo-main">
                <strong>{{ item.title }}</strong>
                <span class="muted">{{ item.ticket_no }}</span>
              </div>
              <div class="todo-meta">
                <el-tag size="small" type="info">{{ PRIORITY_TEXT[item.priority] }}</el-tag>
                <el-tag size="small">{{ STATUS_TEXT[item.status] }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="list-card" v-loading="loading.approvals">
          <template #header>
            <div class="card-head">
              <span>待我审批</span>
              <el-button
                v-if="canApproval"
                link
                type="primary"
                @click="goApprovals(true)"
              >
                查看全部
              </el-button>
            </div>
          </template>
          <el-empty
            v-if="!canApproval"
            description="无审批查看权限"
            :image-size="72"
          />
          <el-empty
            v-else-if="!todoApprovals.length"
            description="暂无待办审批"
            :image-size="72"
          />
          <div v-else class="todo-list">
            <div
              v-for="item in todoApprovals"
              :key="item.id"
              class="todo-item"
              @click="goApprovals(true)"
            >
              <div class="todo-main">
                <strong>{{ item.title }}</strong>
                <span class="muted">{{ item.applicant_name || '申请人' }}</span>
              </div>
              <div class="todo-meta">
                <el-tag size="small" type="warning">
                  {{ APPROVAL_STATUS[item.status] || item.status }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="10">
        <el-card shadow="never" header="快捷入口">
          <div class="shortcuts">
            <el-button
              v-if="canCreateTicket"
              type="primary"
              :icon="Plus"
              @click="router.push('/tickets')"
            >
              新建工单
            </el-button>
            <el-button
              v-if="canCreateApproval"
              type="primary"
              plain
              :icon="Checked"
              @click="router.push('/approvals')"
            >
              发起审批
            </el-button>
            <el-button
              v-if="canAi"
              :icon="ChatDotRound"
              @click="router.push('/ai-chat')"
            >
              AI 助手
            </el-button>
            <el-button
              v-if="canKnowledge"
              :icon="Files"
              @click="router.push('/knowledge')"
            >
              知识库
            </el-button>
            <el-button
              v-if="canTicket"
              :icon="Tickets"
              @click="goTickets(false)"
            >
              全部工单
            </el-button>
            <el-button :icon="Document" @click="router.push('/profile')">
              个人中心
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.welcome-card {
  margin-bottom: 16px;
}

.welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.welcome h2 {
  margin: 0 0 8px;
  font-size: 22px;
}

.welcome p {
  margin: 0;
  font-size: 13px;
}

.stat-row {
  margin-bottom: 16px;
}

.stat-card {
  margin-bottom: 16px;
}

.clickable {
  cursor: pointer;
}

.stat-label {
  color: #909399;
  font-size: 13px;
}

.stat-value {
  font-size: 30px;
  font-weight: 600;
  margin: 6px 0;
  color: #1f2d3d;
}

.stat-hint {
  color: #c0c4cc;
  font-size: 12px;
}

.list-card {
  margin-bottom: 16px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.todo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
}

.todo-item:hover {
  background: #eef5ff;
}

.todo-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.todo-main strong {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.muted {
  color: #909399;
  font-size: 12px;
}

.todo-meta {
  display: flex;
  gap: 6px;
  flex: none;
}

.shortcuts {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.shortcuts .el-button {
  width: 100%;
  margin-left: 0;
  justify-content: flex-start;
}

.text-muted {
  color: #909399;
}
</style>
