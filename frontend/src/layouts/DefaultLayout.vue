<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  ChatDotRound,
  Expand,
  Files,
  Fold,
  Lock,
  Odometer,
  OfficeBuilding,
  Setting,
  User,
} from '@element-plus/icons-vue'

import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => (route.meta.title as string) ?? '')

const canUser = computed(() => auth.has('user:read'))
const canRole = computed(() => auth.has('role:read'))
const canDepartment = computed(() => auth.has('department:read'))
const canOrganization = computed(() => canUser.value || canRole.value || canDepartment.value)
const canSystem = computed(() => auth.has('system:config'))

async function handleLogout(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

function handleCommand(command: string): void {
  if (command === 'logout') {
    void handleLogout()
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<template>
  <el-container class="layout">
    <el-aside :width="app.sidebarCollapsed ? '64px' : '220px'" class="layout-aside">
      <div class="logo">
        <div class="logo-mark">智</div>
        <div v-show="!app.sidebarCollapsed" class="logo-text">
          <strong>智企协同</strong>
          <span>Enterprise AI</span>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="app.sidebarCollapsed"
        :collapse-transition="false"
        router
        background-color="#1f2d3d"
        text-color="#c0c4cc"
        active-text-color="#ffffff"
        class="layout-menu"
      >
        <el-menu-item v-if="auth.has('menu:dashboard')" index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>

        <el-menu-item v-if="auth.has('ai:chat')" index="/ai-chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>AI 助手</template>
        </el-menu-item>

        <el-sub-menu v-if="canOrganization" index="organization">
          <template #title>
            <el-icon><OfficeBuilding /></el-icon>
            <span>组织管理</span>
          </template>
          <el-menu-item v-if="canUser" index="/users">用户管理</el-menu-item>
          <el-menu-item v-if="canRole" index="/roles">角色权限</el-menu-item>
          <el-menu-item v-if="canDepartment" index="/departments">部门管理</el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="canSystem" index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </template>
          <el-menu-item index="/ai-models">AI 模型配置</el-menu-item>
        </el-sub-menu>

        <el-menu-item v-if="auth.has('knowledge:read')" index="/knowledge">
          <el-icon><Files /></el-icon>
          <template #title>知识库</template>
        </el-menu-item>
        <el-menu-item disabled index="/tickets">
          <el-icon><Lock /></el-icon>
          <template #title>工单（规划中）</template>
        </el-menu-item>
        <el-menu-item disabled index="/approvals">
          <el-icon><Lock /></el-icon>
          <template #title>审批（规划中）</template>
        </el-menu-item>

        <el-menu-item index="/profile">
          <el-icon><Setting /></el-icon>
          <template #title>个人中心</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="app.toggleSidebar">
            <Expand v-if="app.sidebarCollapsed" />
            <Fold v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle && route.path !== '/dashboard'">
              {{ currentTitle }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-tag v-if="auth.user?.organization_name" type="info" effect="plain">
            {{ auth.user.organization_name }}
          </el-tag>
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-entry">
              <el-avatar :size="30" :src="auth.user?.avatar ?? undefined">
                {{ auth.displayName.slice(0, 1) }}
              </el-avatar>
              <span class="user-name">{{ auth.displayName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}

.layout-aside {
  background-color: #1f2d3d;
  transition: width 0.2s;
  overflow-x: hidden;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 60px;
  padding: 0 16px;
  color: #fff;
  border-bottom: 1px solid rgb(255 255 255 / 8%);
  overflow: hidden;
}

.logo-mark {
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #6f42c1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  white-space: nowrap;
}

.logo-text span {
  font-size: 11px;
  color: #909399;
}

.layout-menu {
  border-right: none;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.user-name {
  font-size: 14px;
  color: #303133;
}

.layout-main {
  padding: 20px;
  background: #f5f7fa;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
