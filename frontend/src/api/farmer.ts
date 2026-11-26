import { api } from './client'
import type {
  ApiPage,
  DashboardCounts,
  FieldEvidence,
  HerbBatch,
} from './types'

export type BatchInput = Pick<
  HerbBatch,
  | 'herb_name'
  | 'botanical_name'
  | 'plant_part'
  | 'cultivar'
  | 'quality_grade'
  | 'description'
  | 'packaging_details'
  | 'drying_notes'
  | 'gacp_attested'
  | 'quantity'
  | 'unit'
  | 'source_type'
  | 'collection_date'
  | 'collection_time'
  | 'latitude'
  | 'longitude'
  | 'collection_address'
  | 'village'
  | 'district'
  | 'state'
  | 'remarks'
>

export interface FarmerProfile {
  farmer_id: string
  farmer_name: string
  phone_number: string
  address: string
  village: string
  district: string
  state: string
  pincode: string
  land_area: string | null
  land_record_reference: string
  verification_status: string
}

export interface BatchHistory {
  batch: HerbBatch
  history: Array<Record<string, string>>
}

export const farmerApi = {
  dashboard: async () => (
    await api.get<DashboardCounts>('/api/farmers/dashboard/')
  ).data,
  batches: async (params?: { search?: string; status?: string; page?: number }) => (
    await api.get<ApiPage<HerbBatch>>('/api/farmers/batches/', { params })
  ).data,
  batch: async (batchId: string) => (
    await api.get<HerbBatch>(`/api/farmers/batches/detail/${encodeURIComponent(batchId)}/`)
  ).data,
  createBatch: async (input: BatchInput) => (
    await api.post<HerbBatch>('/api/farmers/batches/register/', input)
  ).data,
  updateBatch: async (batchId: string, input: Partial<BatchInput>) => (
    await api.patch<HerbBatch>(
      `/api/farmers/batches/detail/${encodeURIComponent(batchId)}/`,
      input,
    )
  ).data,
  history: async (batchId: string) => (
    await api.get<BatchHistory>(
      `/api/farmers/batches/history/${encodeURIComponent(batchId)}/`,
    )
  ).data,
  evidence: async (batchId: string) => (
    await api.get<FieldEvidence[]>(
      `/api/farmers/batches/detail/${encodeURIComponent(batchId)}/evidence/`,
    )
  ).data,
  uploadEvidence: async (batchId: string, file: File, kind: 'PHOTO' | 'DOCUMENT', label: string) => {
    const body = new FormData()
    body.append('file', file)
    body.append('kind', kind)
    body.append('label', label)
    return (await api.post<FieldEvidence>(
      `/api/farmers/batches/detail/${encodeURIComponent(batchId)}/evidence/`,
      body,
    )).data
  },
  profile: async () => (await api.get<FarmerProfile>('/api/farmers/profile/')).data,
  updateProfile: async (input: Partial<FarmerProfile>) => (
    await api.patch<FarmerProfile>('/api/farmers/profile/', input)
  ).data,
}

