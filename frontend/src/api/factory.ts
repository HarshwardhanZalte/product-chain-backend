import { api } from './client'
import type {
  ApiPage,
  DashboardCounts,
  HerbBatch,
  ManufacturingRecord,
  Product,
  TransferEvent,
} from './types'

export interface ManufacturingInput {
  product_name: string
  process_date: string
  process_description: string
  output_quantity: string
  unit: string
  remarks: string
  facility_line: string
  shift: string
  standard_operating_procedure: string
  solvent_method: string
  target_yield_ratio: string
  process_parameters: Record<string, unknown>
  quality_control_lead: string
  save_as_draft: boolean
  input_batches: Array<{ batch_id: string; quantity_used: string }>
}

export const factoryApi = {
  dashboard: async () => (
    await api.get<DashboardCounts>('/api/factories/dashboard/')
  ).data,
  availableBatches: async () => (
    await api.get<ApiPage<HerbBatch>>('/api/factories/available-batches/')
  ).data,
  pendingTransfers: async () => (
    await api.get<ApiPage<TransferEvent>>('/api/collectors/transfer/pending/')
  ).data,
  receiveTransfer: async (event_id: string, remarks = '') => (
    await api.post('/api/factories/receive-batch/', { event_id, remarks })
  ).data,
  manufacturingRecords: async () => (
    await api.get<ApiPage<ManufacturingRecord>>('/api/factories/manufacturing/list/')
  ).data,
  createManufacturing: async (input: ManufacturingInput) => (
    await api.post<ManufacturingRecord>('/api/factories/manufacturing/create/', input)
  ).data,
  completeManufacturing: async (manufacturing_id: string) => (
    await api.post<ManufacturingRecord>('/api/factories/manufacturing/complete/', {
      manufacturing_id,
    })
  ).data,
  cancelManufacturing: async (manufacturing_id: string) => (
    await api.post<ManufacturingRecord>('/api/factories/manufacturing/cancel/', {
      manufacturing_id,
    })
  ).data,
  products: async () => (
    await api.get<ApiPage<Product>>('/api/products/list/')
  ).data,
  createProduct: async (input: {
    manufacturing_id: string
    product_name: string
    description: string
    product_type: string
    manufacture_date: string
    expiry_date: string
    batch_number: string
    total_quantity: string
    unit: string
    product_image?: File
  }) => {
    const body = new FormData()
    Object.entries(input).forEach(([key, value]) => {
      if (value !== undefined && value !== '') body.append(key, value)
    })
    return (await api.post<Product>('/api/products/create/', body)).data
  },
  regenerateQr: async (productId: string) => (
    await api.post<Product>(`/api/products/qr/${productId}/`)
  ).data,
}
