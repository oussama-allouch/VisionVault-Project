import api from './api'

export const featureService = {
  async getAll(imageId: number) {
    const res = await api.get(`/images/${imageId}/features`)
    return res.data.features
  },
  async getColorHistogram(imageId: number) {
    const res = await api.get(`/images/${imageId}/color-histogram`)
    return res.data
  },
  async getColorMoments(imageId: number) {
    const res = await api.get(`/images/${imageId}/color-moments`)
    return res.data
  },
  async getDominantColors(imageId: number) {
    const res = await api.get(`/images/${imageId}/dominant-colors`)
    return res.data
  },
  async getGLCM(imageId: number) {
    const res = await api.get(`/images/${imageId}/glcm`)
    return res.data
  },
  async getLBP(imageId: number) {
    const res = await api.get(`/images/${imageId}/lbp`)
    return res.data
  },
}
