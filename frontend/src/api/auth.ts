import { api } from './client'
import type {
  ApiDetail,
  LoginResponse,
  OnboardingStatus,
  Tokens,
  User,
} from './types'

export const authApi = {
  login: async (email: string, password: string) => (
    await api.post<LoginResponse>('/api/auth/login/', { email, password })
  ).data,
  register: async (input: {
    name: string
    email: string
    phone_number?: string
    password: string
    role: string
  }) => (await api.post<ApiDetail>('/api/auth/register/', input)).data,
  verifyOtp: async (email: string, otp: string) => (
    await api.post<ApiDetail>('/api/auth/verify-otp/', { email, otp })
  ).data,
  resendOtp: async (email: string) => (
    await api.post<ApiDetail>('/api/auth/resend-otp/', { email })
  ).data,
  forgotPassword: async (email: string) => (
    await api.post<ApiDetail>('/api/auth/forgot-password/', { email })
  ).data,
  resetPassword: async (input: { email: string; otp: string; new_password: string }) => (
    await api.post<ApiDetail>('/api/auth/reset-password/', input)
  ).data,
  logout: async (refresh: string) => (
    await api.post<ApiDetail>('/api/auth/logout/', { refresh })
  ).data,
  refresh: async (refresh: string) => (
    await api.post<Tokens>('/api/auth/refresh/', { refresh })
  ).data,
  profile: async () => (await api.get<User>('/api/auth/profile/')).data,
  onboarding: async () => (
    await api.get<OnboardingStatus>('/api/auth/onboarding/')
  ).data,
}
