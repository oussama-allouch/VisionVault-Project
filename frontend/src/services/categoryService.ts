import api from './api'
import type { Category } from '../types'

export const categoryService = {
  async list() {
    const res = await api.get('/categories')
    return res.data as Category[]
  },
  async create(name: string, parentId?: number) {
    const res = await api.post('/categories', { name, parent_id: parentId })
    return res.data
  },
  async update(id: number, name: string) {
    const res = await api.patch(`/categories/${id}`, { name })
    return res.data
  },
  async remove(id: number) {
    await api.delete(`/categories/${id}`)
  },
}
