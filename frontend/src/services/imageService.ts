import api from './api'
import type { ImageData, PaginatedResponse } from '../types'

export const imageService = {
  async list(params: { page?: number; per_page?: number; category_id?: number; search?: string; sort_by?: string; sort_order?: string }) {
    const res = await api.get('/images', { params })
    return res.data as PaginatedResponse<ImageData>
  },
  async get(id: number) {
    const res = await api.get(`/images/${id}`)
    return res.data as ImageData
  },
  async upload(file: File, categoryId?: number) {
    const form = new FormData()
    form.append('file', file)
    if (categoryId) form.append('category_id', String(categoryId))
    const res = await api.post('/images', form)
    return res.data
  },
  async bulkUpload(files: File[], categoryId?: number) {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    if (categoryId) form.append('category_id', String(categoryId))
    const res = await api.post('/images/bulk-upload', form)
    return res.data
  },
  async remove(id: number) {
    await api.delete(`/images/${id}`)
  },
  async bulkDelete(ids: number[]) {
    const res = await api.post('/images/bulk-delete', { ids })
    return res.data
  },
  async move(id: number, categoryId: number | null) {
    const res = await api.post(`/images/${id}/move`, { category_id: categoryId })
    return res.data
  },
  async download(id: number) {
    const res = await api.get(`/images/${id}/download`, { responseType: 'blob' })
    return res.data
  },
  async bulkDownload(ids: number[]) {
    const res = await api.post('/images/bulk-download', { ids }, { responseType: 'blob' })
    return res.data
  },
}
