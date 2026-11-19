<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { ElMessage } from 'element-plus'

import { resolveErrorMessage } from '@/api/client'
import { departmentsApi, rolesApi } from '@/api/roles'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const auth = useAuthStore()
const router = useRouter()

const stats = reactive({ users: 0, roles: 0, departments: 0 })
const loading = reactive({ users: false, roles: false, departments: false })

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 30, bottom: 30 },
  xAxis: {
    type: 'category',
    data: ['权限', '组织', 'AI 网关', '知识库', '工单', '审批'],
    axisTick: { show: false },
  },
  yAxis: { type: 'value', max: 100, splitLine: { lineStyle: { type: 'dashed' } } },
  series: [
    {
      type: 'bar',
      barWidth: 26,
      data: [100, 100, 20, 0, 0, 0],
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
            下一阶段：AI 模型网关（云端 + Ollama 统一接入），随后是知识库 RAG。
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

.small {
  font-size: 12px;
}
</style>
