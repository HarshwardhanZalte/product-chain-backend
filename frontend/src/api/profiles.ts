import { api } from './client'
import type { Role } from './types'

export type ProfileData = Record<string, string | number | null>

const profileRoutes: Partial<Record<Role, string>> = {
  FARMER: '/api/farmers/profile/',
  COLLECTOR: '/api/collectors/profile/',
  LAB: '/api/labs/profile/',
  FACTORY: '/api/factories/profile/',
}

export const profileApi = {
  get: async (role: Role) => {
    const path = profileRoutes[role]
    if (!path) throw new Error('This account does not have a business profile.')
    return (await api.get<ProfileData>(path)).data
  },
  update: async (role: Role, data: ProfileData) => {
    const path = profileRoutes[role]
    if (!path) throw new Error('This account does not have a business profile.')
    return (await api.patch<ProfileData>(path, data)).data
  },
}
