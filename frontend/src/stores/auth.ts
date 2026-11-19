import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '@/api/auth'
import type { CurrentUser, LoginPayload } from '@/types/user'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '@/utils/token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const loading = ref(false)

  const permissionSet = computed(() => new Set(user.value?.permissions ?? []))
  const isLoggedIn = computed(() => Boolean(getAccessToken()))
  const isSuperuser = computed(() => user.value?.is_superuser ?? false)
  const displayName = computed(() => user.value?.real_name || user.value?.username || '未登录')
  const roles = computed(() => user.value?.roles ?? [])

  async function login(payload: LoginPayload): Promise<void> {
    const { data } = await authApi.login(payload)
    setTokens(data.access_token, data.refresh_token)
    await fetchMe()
  }

  async function fetchMe(): Promise<void> {
    if (!getAccessToken()) {
      return
    }
    loading.value = true
    try {
      const { data } = await authApi.me()
      user.value = data
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
    fetchMe,
    logout,
    reset,
    has,
    hasAny,
  }
})
