import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    icon?: string
    permission?: string
    public?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '工作台', icon: 'Odometer', permission: 'menu:dashboard' },
      },
      {
        path: 'ai-chat',
        name: 'AiChat',
        component: () => import('@/views/AiChatView.vue'),
        meta: { title: 'AI 助手', icon: 'ChatDotRound', permission: 'ai:chat' },
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/KnowledgeView.vue'),
        meta: { title: '知识库', icon: 'Files', permission: 'knowledge:read' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/UserListView.vue'),
        meta: { title: '用户管理', icon: 'User', permission: 'user:read' },
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('@/views/RoleListView.vue'),
        meta: { title: '角色权限', icon: 'Lock', permission: 'role:read' },
      },
      {
        path: 'departments',
        name: 'Departments',
        component: () => import('@/views/DepartmentView.vue'),
        meta: { title: '部门管理', icon: 'OfficeBuilding', permission: 'department:read' },
      },
      {
        path: 'ai-models',
        name: 'AiModels',
        component: () => import('@/views/AiModelConfigView.vue'),
        meta: { title: 'AI 模型配置', icon: 'Setting', permission: 'system:config' },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/ProfileView.vue'),
        meta: { title: '个人中心', icon: 'Setting' },
      },
    ],
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/ForbiddenView.vue'),
    meta: { title: '无权访问', public: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在', public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    // 登录页：已登录用户直接进工作台
    const guestOnly = to.path === '/login'
    if (guestOnly && auth.isLoggedIn) {
      return { path: '/dashboard' }
    }
    return true
  }

  if (!auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.reset()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  if (to.meta.permission && !auth.has(to.meta.permission)) {
    return { path: '/403' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · 智企协同`
    : '智企协同 Enterprise AI'
})

export default router
