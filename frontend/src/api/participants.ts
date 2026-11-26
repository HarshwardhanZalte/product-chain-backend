import { api } from './client'
import type { ApiPage, Participant } from './types'

export const participantsApi = {
  list: async (role: 'COLLECTOR' | 'FACTORY' | 'LAB', search = '') => (
    await api.get<ApiPage<Participant>>('/api/participants/', {
      params: { role, search: search || undefined },
    })
  ).data,
}
