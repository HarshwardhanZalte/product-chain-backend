import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { Tokens } from './types'

const TOKEN_STORAGE_KEY = 'product-chain.tokens'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

interface StoredAuth extends Tokens {}

export function readTokens(): StoredAuth | null {
  const raw = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (!raw) return null
  try {
    const parsed: unknown = JSON.parse(raw)
    if (
      typeof parsed === 'object'
      && parsed !== null
      && 'access' in parsed
      && 'refresh' in parsed
      && typeof parsed.access === 'string'
      && typeof parsed.refresh === 'string'
    ) {
      return { access: parsed.access, refresh: parsed.refresh }
    }
  } catch {
    clearTokens()
  }
  return null
}

export function writeTokens(tokens: Tokens): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens))
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { Accept: 'application/json' },
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const tokens = readTokens()
  if (tokens?.access) config.headers.Authorization = `Bearer ${tokens.access}`
  return config
})

let refreshRequest: Promise<string> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined
    const tokens = readTokens()
    if (
      error.response?.status !== 401
      || !original
      || original._retry
      || !tokens?.refresh
      || original.url?.includes('/api/auth/refresh/')
    ) {
      return Promise.reject(error)
    }

    original._retry = true
    try {
      refreshRequest ??= axios
        .post<Tokens>(`${API_BASE_URL}/api/auth/refresh/`, { refresh: tokens.refresh })
        .then(({ data }) => {
          const nextTokens = { access: data.access, refresh: data.refresh ?? tokens.refresh }
          writeTokens(nextTokens)
          return nextTokens.access
        })
        .finally(() => {
          refreshRequest = null
        })
      const access = await refreshRequest
      original.headers.Authorization = `Bearer ${access}`
      return api(original)
    } catch (refreshError) {
      clearTokens()
      window.dispatchEvent(new CustomEvent('product-chain:auth-expired'))
      return Promise.reject(refreshError)
    }
  },
)

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const body: unknown = error.response?.data
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const detail = body.detail
      if (typeof detail === 'string') return detail
    }
    if (typeof body === 'object' && body !== null) {
      for (const [field, value] of Object.entries(body)) {
        if (typeof value === 'string') return `${field}: ${value}`
        if (Array.isArray(value) && typeof value[0] === 'string') {
          return `${field}: ${value[0]}`
        }
      }
    }
    return error.message || 'The request could not be completed.'
  }
  return error instanceof Error ? error.message : 'Something went wrong.'
}
