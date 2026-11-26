import { api } from './client'
import type { ProductVerification } from './types'

export const productApi = {
  verify: async (qrReference: string) => (
    await api.get<ProductVerification>(
      `/api/products/verify/${encodeURIComponent(qrReference)}/`,
    )
  ).data,
  downloadAsset: async (productId: string, asset: 'qr' | 'image') => (
    await api.get<Blob>(`/api/products/${encodeURIComponent(productId)}/assets/${asset}/`, {
      responseType: 'blob',
    })
  ).data,
}

export function downloadFromUrl(url: string, filename: string): void {
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.target = '_blank'
  anchor.rel = 'noreferrer'
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
}

export function downloadBlob(data: Blob, filename: string): void {
  const url = URL.createObjectURL(data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
