import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { authApi } from '../api/auth'
import { clearTokens, getApiErrorMessage, readTokens, writeTokens } from '../api/client'
import type { Role, User } from '../api/types'

interface AuthContextValue {
  user: User | null
  ready: boolean
  sessionError: string | null
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  reloadSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)
  const [sessionError, setSessionError] = useState<string | null>(null)

  const reloadSession = useCallback(async () => {
    if (!readTokens()) {
      setUser(null)
      setSessionError(null)
      setReady(true)
      return
    }
    setReady(false)
    setSessionError(null)
    try {
      setUser(await authApi.profile())
    } catch (error) {
      setUser(null)
      setSessionError(getApiErrorMessage(error))
    } finally {
      setReady(true)
    }
  }, [])

  useEffect(() => {
    void reloadSession()
  }, [reloadSession])

  useEffect(() => {
    const expire = () => {
      setUser(null)
      setSessionError('Your session expired. Sign in again to continue.')
    }
    window.addEventListener('product-chain:auth-expired', expire)
    return () => window.removeEventListener('product-chain:auth-expired', expire)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login(email, password)
    writeTokens(response.tokens)
    setUser(response.user)
    setSessionError(null)
    return response.user
  }, [])

  const logout = useCallback(async () => {
    const tokens = readTokens()
    try {
      if (tokens?.refresh) await authApi.logout(tokens.refresh)
    } finally {
      clearTokens()
      setUser(null)
      setSessionError(null)
    }
  }, [])

  const value = useMemo(
    () => ({ user, ready, sessionError, login, logout, reloadSession }),
    [user, ready, sessionError, login, logout, reloadSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider.')
  return value
}

export function roleHome(role: Role): string {
  const paths: Record<Role, string> = {
    FARMER: '/farmer',
    COLLECTOR: '/collector',
    LAB: '/lab',
    FACTORY: '/factory',
    ADMIN: '/admin',
  }
  return paths[role]
}
