import { reactive, computed } from 'vue'
import { authApi } from '@/api'

const TOKEN_KEY = 'crawler_mgmt_token'
const USER_KEY = 'crawler_mgmt_user'

const state = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: JSON.parse(localStorage.getItem(USER_KEY) || 'null')
})

export const userStore = {
  state,
  isLogin: computed(() => !!state.token),
  isAdmin: computed(() => state.user?.role === 'admin'),
  username: computed(() => state.user?.nickname || state.user?.username || ''),
  user_id: computed(() => state.user?.id || 0),

  /** 登录：写入 token & user */
  async login(payload) {
    const data = await authApi.login(payload)
    state.token = data.token
    state.user = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    return data
  },

  /** 退出登录：清空本地状态 */
  logout() {
    state.token = ''
    state.user = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },

  /** 拉取最新用户信息（用于刷新页面后恢复） */
  async fetchMe() {
    if (!state.token) return null
    try {
      const u = await authApi.me()
      state.user = u
      localStorage.setItem(USER_KEY, JSON.stringify(u))
      return u
    } catch {
      this.logout()
      return null
    }
  },

  /** 更新本地缓存的 user 局部字段 */
  patchUser(patch) {
    state.user = { ...(state.user || {}), ...patch }
    localStorage.setItem(USER_KEY, JSON.stringify(state.user))
  }
}
