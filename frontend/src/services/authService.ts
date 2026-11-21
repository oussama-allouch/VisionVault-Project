import api from './api'
import type { User } from '../types'

export const authService = {
  async login(email: string, password: string) {
    const res = await api.post('/auth/login', { email, password })
    return res.data as { access_token: string; refresh_token: string; user: User }
  },
  async register(email: string, password: string) {
    const res = await api.post('/auth/register', { email, password })
    return res.data
  },
  async me() {
    const res = await api.get('/auth/me')
    return res.data as User
  },
  async logout() {
    await api.post('/auth/logout')
  }
}
