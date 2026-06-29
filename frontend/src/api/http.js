import axios from 'axios'
import { ElMessage } from 'element-plus'

const TOKEN_KEY = 'crawler_mgmt_token'

const http = axios.create({
  baseURL: '/api',
  timeout: 60000
})

// 请求拦截器：自动带上 token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      ElMessage.error(body.msg || '请求失败')
      return Promise.reject(new Error(body.msg || '请求失败'))
    }
    return body
  },
  (error) => {
    const status = error?.response?.status
    const msg = error?.response?.data?.detail || error.message || '网络错误'
    // 401：token 失效，跳登录
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('crawler_mgmt_user')
      ElMessage.error('登录已过期，请重新登录')
      // 避免在登录页重复跳转
      if (!window.location.pathname.startsWith('/login')) {
        setTimeout(() => {
          window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`
        }, 600)
      }
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export { TOKEN_KEY }
export default http
