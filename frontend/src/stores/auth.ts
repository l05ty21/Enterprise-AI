import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '@/api/auth'
import type { CurrentUser, LoginPayload, RegisterPayload } from '@/types/user'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '@/utils/token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const loading = ref(false)
  // 登录态必须由响应式变量驱动：直接读 localStorage 的 computed 没有依赖，
  // 会在首次求值后永久缓存，导致登录成功后守卫仍判定为未登录、跳回登录页。
  const accessToken = ref<string | null>(getAccessToken())

  const permissionSet = computed(() => new Set(user.value?.permissions ?? []))
  const isLoggedIn = computed(() => Boolean(accessToken.value))
  const isSuperuser = computed(() => user.value?.is_superuser ?? false)
  const displayName = computed(() => user.value?.real_name || user.value?.username || '未登录')
  const roles = computed(() => user.value?.roles ?? [])

  async function login(payload: LoginPayload): Promise<void> {
    const { data } = await authApi.login(payload)
    setTokens(data.access_token, data.refresh_token)
    accessToken.value = data.access_token
    await fetchMe()
  }

  /** 注册成功后后端直接返回令牌，这里沿用登录后的同一套状态初始化 */
  async function register(payload: RegisterPayload): Promise<void> {
    const { data } = await authApi.register(payload)
    setTokens(data.access_token, data.refresh_token)
    accessToken.value = data.access_token
    await fetchMe()
  }

  async function fetchMe(): Promise<void> {
    if (!getAccessToken()) {
      accessToken.value = null
      return
    }
    loading.value = true
    try {
      const { data } = await authApi.me()
      user.value = data
      accessToken.value = getAccessToken()
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout(getRefreshToken())
    } catch {
      // 令牌可能已经过期，退出登录时忽略错误
    } finally {
      reset()
    }
  }

  function reset(): void {
    clearTokens()
    accessToken.value = null
    user.value = null
  }

  function has(code?: string | null): boolean {
    if (!code) {
      return true
    }
    return isSuperuser.value || permissionSet.value.has(code)
  }

  function hasAny(codes: string[]): boolean {
    if (isSuperuser.value) {
      return true
    }
    return codes.some((code) => permissionSet.value.has(code))
  }

  return {
    user,
    loading,
    permissionSet,
    isLoggedIn,
    isSuperuser,
    displayName,
    roles,
    login,
    register,
    fetchMe,
    logout,
    reset,
    has,
    hasAny,
  }
})
