import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

import type { ApiError } from '@/types/api'
import type { TokenPair } from '@/types/user'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '@/utils/token'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

interface RetryConfig extends AxiosRequestConfig {
  _retry?: boolean
}

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshing = false
let pendingQueue: Array<(token: string | null) => void> = []

async function requestNewToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return null
  }
  try {
    const { data } = await axios.post<TokenPair>(`${baseURL}/auth/refresh`, {
      refresh_token: refreshToken,
    })
    setTokens(data.access_token, data.refresh_token)
    return data.access_token
  } catch {
    return null
  }
}

function redirectToLogin(): void {
  clearTokens()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.assign('/login')
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const config = error.config as RetryConfig | undefined
    const status = error.response?.status
    const url = config?.url ?? ''
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/refresh')

    if (status === 401 && config && !config._retry && !isAuthEndpoint) {
      config._retry = true

      if (refreshing) {
        const token = await new Promise<string | null>((resolve) => {
          pendingQueue.push(resolve)
        })
        if (token) {
          config.headers = { ...config.headers, Authorization: `Bearer ${token}` }
          return apiClient(config)
        }
        redirectToLogin()
        return Promise.reject(error)
      }

      refreshing = true
      const token = await requestNewToken()
      refreshing = false
      pendingQueue.forEach((resolve) => resolve(token))
      pendingQueue = []

      if (token) {
        config.headers = { ...config.headers, Authorization: `Bearer ${token}` }
        return apiClient(config)
      }

      ElMessage.error('登录状态已失效，请重新登录')
      redirectToLogin()
      return Promise.reject(error)
    }

    if (!isAuthEndpoint) {
      const message = error.response?.data?.message ?? '网络异常，请稍后重试'
      ElMessage.error(message)
    }

    return Promise.reject(error)
  },
)

export function resolveErrorMessage(error: unknown, fallback = '操作失败'): string {
  const axiosError = error as AxiosError<ApiError>
  const detail = axiosError?.response?.data?.detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { field?: string; message?: string }
    return `${first.field ?? ''} ${first.message ?? ''}`.trim() || fallback
  }
  return axiosError?.response?.data?.message ?? fallback
}
