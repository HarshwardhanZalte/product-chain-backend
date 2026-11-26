import { api } from './client'
import type { ApiPage, DashboardCounts, LabMeasurement, LabTest } from './types'

export interface LabResultInput {
  test_id: string
  test_result: string
  result_summary: string
  remarks: string
  measurements: LabMeasurement[]
  certificate_file?: File
}

export const labApi = {
  dashboard: async () => (
    await api.get<DashboardCounts>('/api/labs/dashboard/')
  ).data,
  requests: async (params?: { search?: string; ordering?: string; page?: number }) => (
    await api.get<ApiPage<LabTest>>('/api/labs/requests/', { params })
  ).data,
  history: async (params?: { page?: number }) => (
    await api.get<ApiPage<LabTest>>('/api/labs/test-history/', { params })
  ).data,
  submitBatch: async (input: {
    batch_id: string
    laboratory_id: string
    test_type: string
    test_date: string
    test_parameters: Record<string, unknown>
  }) => (await api.post<LabTest>('/api/labs/submit-batch/', input)).data,
  test: async (testId: string) => (
    await api.get<LabTest>(`/api/labs/tests/${testId}/`)
  ).data,
  submitResult: async (input: LabResultInput) => {
    const { certificate_file, ...result } = input
    if (!certificate_file) {
      return (await api.post<LabTest>('/api/labs/submit-result/', result)).data
    }

    const body = new FormData()
    Object.entries(result).forEach(([key, value]) => {
      body.append(key, typeof value === 'string' ? value : JSON.stringify(value))
    })
    body.append('certificate_file', certificate_file)
    return (await api.post<LabTest>('/api/labs/submit-result/', body)).data
  },
  approve: async (test_id: string, remarks = '') => (
    await api.post<LabTest>('/api/labs/approve-test/', { test_id, remarks })
  ).data,
  reject: async (test_id: string, remarks: string) => (
    await api.post<LabTest>('/api/labs/reject-test/', { test_id, remarks })
  ).data,
  downloadCertificate: async (testId: string) => (
    await api.get<Blob>(`/api/private/lab-tests/${testId}/certificate/`, {
      responseType: 'blob',
    })
  ).data,
}
