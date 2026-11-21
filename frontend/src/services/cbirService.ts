import api from './api'
import type { SearchResult } from '../types'

export const cbirService = {
  async search(queryImageId: number, numResults = 25) {
    const res = await api.post('/cbir/search', { query_image_id: queryImageId, num_results: numResults })
    return res.data as {
      session_id: number
      query_image: any
      results: SearchResult[]
      total_results: number
      duration_ms: number
    }
  },
  async searchUpload(file: File, numResults = 25) {
    const form = new FormData()
    form.append('file', file)
    form.append('num_results', String(numResults))
    const res = await api.post('/cbir/search/upload', form)
    return res.data
  },
  async feedback(sessionId: number, iteration: number, relevantIds: number[], nonRelevantIds: number[], numResults = 25) {
    const res = await api.post('/cbir/feedback', {
      session_id: sessionId,
      iteration,
      relevant_ids: relevantIds,
      non_relevant_ids: nonRelevantIds,
      num_results: numResults,
    })
    return res.data
  },
  async getSession(sessionId: number) {
    const res = await api.get(`/cbir/sessions/${sessionId}`)
    return res.data
  },
  async getHistory(sessionId: number) {
    const res = await api.get(`/cbir/sessions/${sessionId}/history`)
    return res.data
  },
}
