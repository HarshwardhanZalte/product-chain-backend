import { api } from './client'
import type { ApiPage, DashboardCounts, HerbBatch, TransferEvent } from './types'

export const collectorApi = {
  dashboard: async () => (
    await api.get<DashboardCounts>('/api/collectors/dashboard/')
  ).data,
  availableBatches: async () => (
    await api.get<ApiPage<HerbBatch>>('/api/collectors/available-batches/')
  ).data,
  pendingTransfers: async () => (
    await api.get<ApiPage<TransferEvent>>('/api/collectors/transfer/pending/')
  ).data,
  history: async () => (
    await api.get<ApiPage<TransferEvent>>('/api/collectors/transfer/history/')
  ).data,
  initiate: async (input: {
    batch_id: string
    to_party: number
    quantity: string
    transfer_location: string
    remarks: string
  }) => (await api.post<TransferEvent>('/api/collectors/transfer/initiate/', input)).data,
  accept: async (event_id: string, remarks = '') => (
    await api.post<TransferEvent>('/api/collectors/transfer/accept/', { event_id, remarks })
  ).data,
  reject: async (event_id: string, remarks: string) => (
    await api.post<TransferEvent>('/api/collectors/transfer/reject/', { event_id, remarks })
  ).data,
}
