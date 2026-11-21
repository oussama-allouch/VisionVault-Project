import api from './api'

export const indexService = {
  async importDataset() {
    const res = await api.post('/index/import')
    return res.data
  },
  async rebuild() {
    const res = await api.post('/index/rebuild')
    return res.data
  },
  async status() {
    const res = await api.get('/index/status')
    return res.data
  },
}
