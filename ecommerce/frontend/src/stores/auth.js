import { defineStore } from 'pinia'
import api, { TOKEN_KEY, ME_KEY, clearAuth } from '../api'

/**
 * 鉴权 Store
 * 统一管理 token / 当前用户，替换各页面散落的 localStorage 直读。
 */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    me: JSON.parse(localStorage.getItem(ME_KEY) || 'null'),
  }),

  getters: {
    isLoggedIn: (s) => !!s.me,
    roleLabel: (s) => ({ admin: '管理员', operator: '运营', viewer: '访客' }[s.me?.role] || s.me?.role || ''),
  },

  actions: {
    /** 登录：换取 token 后拉取用户信息 */
    async login(username, password) {
      const res = await api.post('/auth/login', { username, password })
      this.token = res.access_token
      localStorage.setItem(TOKEN_KEY, res.access_token)
      const me = await api.get('/auth/me')
      this.me = me
      localStorage.setItem(ME_KEY, JSON.stringify(me))
      return me
    },

    /** 路由守卫用：本地有身份直接放行，否则校验令牌 */
    async restore() {
      if (this.me) return true
      try {
        const me = await api.get('/auth/me', { __silent: true })
        this.me = me
        localStorage.setItem(ME_KEY, JSON.stringify(me))
        return true
      } catch {
        return false
      }
    },

    logout() {
      this.token = ''
      this.me = null
      clearAuth()
    },
  },
})
