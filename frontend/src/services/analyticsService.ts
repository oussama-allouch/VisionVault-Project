import api from './api'
import type { AnalyticsOverview } from '../types'

export const analyticsService = {
  async overview() {
    const res = await api.get('/analytics/overview')
    return res.data as AnalyticsOverview
  },
  async evaluation() {
    const res = await api.get('/analytics/evaluation')
    return res.data
  },
}
