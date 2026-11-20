<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { ElMessage } from 'element-plus'

import { aiApi } from '@/api/ai'
import { resolveErrorMessage } from '@/api/client'
import { knowledgeApi } from '@/api/knowledge'
import { departmentsApi, rolesApi } from '@/api/roles'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const auth = useAuthStore()
const router = useRouter()

const stats = reactive({
  users: 0,
  roles: 0,
  departments: 0,
  knowledgeBases: 0,
  knowledgeDocuments: 0,
  knowledgeChunks: 0,
  aiChatModels: 0,
  aiEmbeddingModels: 0,
  aiLocalModels: 0,
})
const loading = reactive({
  users: false,
  roles: false,
  departments: false,
  knowledge: false,
  ai: false,
})

/** 知识库建设进度：未建库 0；已建库 50；已解析出切片 75；切片已向量化、可语义检索 100 */
const knowledgeProgress = computed(() => {
  if (!stats.knowledgeBases) return 0
  if (!stats.knowledgeDocuments) return 50
  if (!stats.knowledgeChunks) return 75
  return 100
})

/** 没有 system:config 权限时读不到模型配置，沿用原来的静态基线，避免把别人的数字看成 0 */
const AI_GATEWAY_FALLBACK = 20

/**
 * AI 网关进度：云端对话 40 + 云端向量 40 + 本地 Ollama 20。
 * 只统计「已启用 且（有 Key 或本来就不需要 Key 的 Ollama）」的配置。
 */
const aiGatewayProgress = computed(() => {
  if (!auth.has('system:config')) return AI_GATEWAY_FALLBACK
  let progress = 0
  if (stats.aiChatModels) progress += 40
  if (stats.aiEmbeddingModels) progress += 40
  if (stats.aiLocalModels) progress += 20
  return progress
})

const stageNames = ['权限', '组织', 'AI 网关', '知识库', '工单', '审批']

/**
 * 阶段建设进度：知识库、AI 网关按库里真实配置计算，其余为阶段性目标值。
 * 工单 / 审批尚未开发，固定 0。
 */
const stageValues = computed<Record<string, number>>(() => ({
  权限: 100,
  组织: 100,
  'AI 网关': aiGatewayProgress.value,
  知识库: knowledgeProgress.value,
  // 工单/审批核心流程已上线：提交、指派、流转、评论 / 发起、审批、驳回
  // 还差附件上传与多级审批，所以按 80 计
  工单: 80,
  审批: 80,
}))

interface BarParam {
  name: string
  value: number
}

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter: (params: unknown) => {
      const list = (Array.isArray(params) ? params : [params]) as BarParam[]
      const item = list[0]
      if (!item) return ''
      const detail: Record<string, string> = {
        知识库: stats.knowledgeBases
          ? `${stats.knowledgeBases} 个知识库 · ${stats.knowledgeDocuments} 篇文档 · ${stats.knowledgeChunks} 个切片`
          : '尚未创建知识库',
        'AI 网关': auth.has('system:config')
          ? `云端对话 ${stats.aiChatModels} 个 · 云端向量 ${stats.aiEmbeddingModels} 个 · Ollama ${
              stats.aiLocalModels ? '已接入' : '待接入'
            }`
          : '无权限查看模型配置',
        工单: '提交 / 指派 / 流转 / 评论已上线，附件待补',
        审批: '发起 / 通过 / 驳回已上线，多级审批待补',
      }
      const note = detail[item.name]
      return `${item.name}：${item.value}%${note ? `<br/><span style="color:#909399">${note}</span>` : ''}`
    },
  },
  grid: { left: 40, right: 20, top: 30, bottom: 30 },
  xAxis: {
    type: 'category',
    data: stageNames,
    axisTick: { show: false },
  },
  yAxis: { type: 'value', max: 100, splitLine: { lineStyle: { type: 'dashed' } } },
  series: [
    {
      type: 'bar',
      barWidth: 26,
      data: stageNames.map((name) => stageValues.value[name]),
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: '#409eff',
      },
    },
  ],
}))

async function loadStats(): Promise<void> {
  if (auth.has('user:read')) {
    loading.users = true
    try {
      const { data } = await usersApi.list({ page: 1, page_size: 1 })
      stats.users = data.total
    } catch (error) {
      ElMessage.warning(resolveErrorMessage(error, '用户统计加载失败'))
    } finally {
      loading.users = false
    }
  }

  if (auth.has('role:read')) {
    loading.roles = true
    try {
      const { data } = await rolesApi.list()
      stats.roles = data.length
    } catch {
      // 忽略单个统计失败，不影响其他卡片
    } finally {
      loading.roles = false
    }
  }

  if (auth.has('department:read')) {
    loading.departments = true
    try {
      const { data } = await departmentsApi.tree()
      const count = (nodes: typeof data): number =>
        nodes.reduce((sum, node) => sum + 1 + count(node.children), 0)
      stats.departments = count(data)
    } catch {
      // 同上
    } finally {
      loading.departments = false
    }
  }

  if (auth.has('knowledge:read')) {
    loading.knowledge = true
    try {
      const { data } = await knowledgeApi.listBases()
      stats.knowledgeBases = data.length
      stats.knowledgeDocuments = data.reduce((sum, kb) => sum + kb.document_count, 0)
      stats.knowledgeChunks = data.reduce((sum, kb) => sum + kb.chunk_count, 0)
    } catch {
      // 同上
    } finally {
      loading.knowledge = false
    }
  }

  if (auth.has('system:config')) {
    loading.ai = true
    try {
      const { data } = await aiApi.listModels()
      const usable = data.filter(
        (model) => model.is_enabled && (model.has_api_key || model.provider === 'ollama'),
      )
      stats.aiChatModels = usable.filter((model) => model.model_type === 'llm').length
      stats.aiEmbeddingModels = usable.filter((model) => model.model_type === 'embedding').length
      stats.aiLocalModels = usable.filter((model) => model.provider === 'ollama').length
    } catch {
      // 同上
    } finally {
      loading.ai = false
    }
  }
}

onMounted(loadStats)
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
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" v-loading="loading.users">
          <div class="stat-label">企业用户</div>
          <div class="stat-value">{{ auth.has('user:read') ? stats.users : '—' }}</div>
          <div class="stat-hint">账号总数</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" v-loading="loading.roles">
          <div class="stat-label">角色</div>
          <div class="stat-value">{{ auth.has('role:read') ? stats.roles : '—' }}</div>
          <div class="stat-hint">可分配角色</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" v-loading="loading.departments">
          <div class="stat-label">部门</div>
          <div class="stat-value">{{ auth.has('department:read') ? stats.departments : '—' }}</div>
          <div class="stat-hint">含子部门</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover">
          <div class="stat-label">权限点</div>
          <div class="stat-value">{{ auth.user?.permissions.length ?? 0 }}</div>
          <div class="stat-hint">当前账号可用</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :xs="24" :md="14">
        <el-card shadow="never" header="阶段建设进度">
          <VChart :option="chartOption" autoresize style="height: 280px" />
          <p
            v-if="auth.has('knowledge:read') || auth.has('system:config')"
            class="chart-note"
          >
            <span v-if="auth.has('knowledge:read')">
              知识库：{{ stats.knowledgeBases }} 个库 · {{ stats.knowledgeDocuments }} 篇文档 ·
              {{ stats.knowledgeChunks }} 个切片
            </span>
            <span v-if="auth.has('knowledge:read') && auth.has('system:config')"> ｜ </span>
            <span v-if="auth.has('system:config')">
              AI 网关：对话 {{ stats.aiChatModels }} · 向量 {{ stats.aiEmbeddingModels }} ·
              Ollama {{ stats.aiLocalModels ? '已接入' : '待接入' }}
            </span>
          </p>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="10">
        <el-card shadow="never" header="快捷入口">
          <el-space direction="vertical" fill size="large" style="width: 100%">
            <el-button v-if="auth.has('user:read')" @click="router.push('/users')">
              用户管理
            </el-button>
            <el-button v-if="auth.has('role:read')" @click="router.push('/roles')">
              角色权限
            </el-button>
            <el-button v-if="auth.has('department:read')" @click="router.push('/departments')">
              部门管理
            </el-button>
            <el-button @click="router.push('/profile')">个人中心</el-button>
          </el-space>

          <el-divider />
          <p class="text-muted small">
            已完成：权限体系、组织架构、知识库 RAG；AI 网关已接入云端模型，Ollama 待接入；
            下一阶段：工单与审批。
          </p>
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

.stat-row .el-card {
  margin-bottom: 16px;
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

.chart-note {
  margin: 4px 0 0;
  font-size: 12px;
  color: #606266;
}

.small {
  font-size: 12px;
}
</style>
