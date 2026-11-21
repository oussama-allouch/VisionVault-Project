import api from './api'

export const processingService = {
  async crop(imageId: number, x: number, y: number, width: number, height: number) {
    const res = await api.post(`/images/${imageId}/crop`, { x, y, width, height })
    return res.data
  },
  async resize(imageId: number, width: number, height: number, maintainAspect = true) {
    const res = await api.post(`/images/${imageId}/resize`, { width, height, maintain_aspect: maintainAspect })
    return res.data
  },
  async transform(imageId: number, operations: { type: string; angle?: number; direction?: string; factor?: number }[]) {
    const res = await api.post(`/images/${imageId}/transform`, { operations })
    return res.data
  },
}
