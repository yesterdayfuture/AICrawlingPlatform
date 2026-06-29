import http from './http'
import axios from 'axios'

const TOKEN_KEY = 'crawler_mgmt_token'

// 带上 token 的导出请求
function authedAxios(config) {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers = { ...(config.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  return axios({ ...config, headers })
}

// ============ 通用列表参数构造 ============
export const buildListParams = (query) => ({
  page: query.page,
  page_size: query.page_size,
  name: query.name || undefined,
  description: query.description || undefined,
  search_mode: query.search_mode || 'fuzzy',
  status: query.status || undefined,
  start_time: query.start_time || undefined,
  end_time: query.end_time || undefined
})

// ============ 通用导出参数构造 ============
// 返回 axios 请求配置（响应类型 blob），由调用方拿 res.data 直接保存
export const buildExportConfig = (url, { format, filename, query, ids }) => {
  const params = { format, filename }
  if (query) {
    // 通用过滤参数
    Object.assign(params, {
      name: query.name || undefined,
      description: query.description || undefined,
      search_mode: query.search_mode || 'fuzzy',
      status: query.status || undefined,
      start_time: query.start_time || undefined,
      end_time: query.end_time || undefined
    })
    // 各模块特有的过滤参数
    if (query.task_id) params.task_id = query.task_id
    if (query.task_result_id) params.task_result_id = query.task_result_id
  }
  if (ids && ids.length) params.ids = ids.join(',')
  return { method: 'get', url, params, responseType: 'blob' }
}

// 实际发起导出请求，返回 Blob
export const requestExport = async (url, opts) => {
  const res = await authedAxios({ ...buildExportConfig(url, opts), baseURL: '/api' })
  return { blob: res.data, filename: parseFilename(res) }
}

function parseFilename(res) {
  const cd = res.headers['content-disposition'] || ''
  const m = cd.match(/filename\*=UTF-8''([^;]+)/i) || cd.match(/filename="?([^";]+)"?/i)
  if (m) {
    try { return decodeURIComponent(m[1]) } catch { return m[1] }
  }
  return 'download'
}

// ============ 总览 ============
export const dashboardApi = {
  stats: (params) => http.get('/dashboard/stats', { params }),
  trend: (params) => http.get('/dashboard/trend', { params }),
  export: (opts) => requestExport('/dashboard/export', opts)
}

// ============ 认证 ============
export const authApi = {
  login: (data) => http.post('/auth/login', data),    // 返回 { token, user }
  me: () => http.get('/auth/me'),
  updateMe: (data) => http.put('/auth/me', data),
  changePassword: (data) => http.put('/auth/password', data)
}

// ============ 用户管理（管理员） ============
export const userApi = {
  list: (params) => http.get('/users', { params }),
  create: (data) => http.post('/users', data),
  update: (id, data) => http.put(`/users/${id}`, data),
  remove: (id) => http.delete(`/users/${id}`),
  toggleStatus: (id) => http.put(`/users/${id}/toggle-status`)
}

// ============ 爬虫 ============
export const crawlerApi = {
  list: (params) => http.get('/crawlers', { params }),
  all: () => http.get('/crawlers/all'),
  get: (id) => http.get(`/crawlers/${id}`),
  create: (data) => http.post('/crawlers', data),
  update: (id, data) => http.put(`/crawlers/${id}`, data),
  remove: (id) => http.delete(`/crawlers/${id}`),
  export: (opts) => requestExport('/crawlers/export', opts)
}

// ============ 大模型 ============
export const modelApi = {
  list: (params) => http.get('/models', { params }),
  all: () => http.get('/models/all'),
  get: (id) => http.get(`/models/${id}`),
  create: (data) => http.post('/models', data),
  update: (id, data) => http.put(`/models/${id}`, data),
  remove: (id) => http.delete(`/models/${id}`),
  export: (opts) => requestExport('/models/export', opts)
}

// ============ 提示词 ============
export const promptApi = {
  list: (params) => http.get('/prompts', { params }),
  all: () => http.get('/prompts/all'),
  get: (id) => http.get(`/prompts/${id}`),
  create: (data) => http.post('/prompts', data),
  update: (id, data) => http.put(`/prompts/${id}`, data),
  remove: (id) => http.delete(`/prompts/${id}`),
  export: (opts) => requestExport('/prompts/export', opts)
}

// ============ 任务 ============
export const taskApi = {
  list: (params) => http.get('/tasks', { params }),
  get: (id) => http.get(`/tasks/${id}`),
  create: (data) => http.post('/tasks', data),
  update: (id, data) => http.put(`/tasks/${id}`, data),
  remove: (id) => http.delete(`/tasks/${id}`),
  run: (id) => http.post(`/tasks/${id}/run`),
  export: (opts) => requestExport('/tasks/export', opts)
}

// ============ 任务结果 ============
export const taskResultApi = {
  list: (params) => http.get('/task-results', { params }),
  get: (id) => http.get(`/task-results/${id}`),
  update: (id, data) => http.put(`/task-results/${id}`, data),
  remove: (id) => http.delete(`/task-results/${id}`),
  parse: (id, data) => http.post(`/task-results/${id}/parse`, data),
  export: (opts) => requestExport('/task-results/export', opts)
}

// ============ 解析结果 ============
export const parseResultApi = {
  list: (params) => http.get('/parse-results', { params }),
  get: (id) => http.get(`/parse-results/${id}`),
  create: (data) => http.post('/parse-results', data),
  update: (id, data) => http.put(`/parse-results/${id}`, data),
  remove: (id) => http.delete(`/parse-results/${id}`),
  export: (opts) => requestExport('/parse-results/export', opts)
}

// ============ 操作日志（管理员） ============
export const operationLogApi = {
  list: (params) => http.get('/operation-logs', { params }),
  filters: () => http.get('/operation-logs/filters'),
  get: (id) => http.get(`/operation-logs/${id}`),
  remove: (id) => http.delete(`/operation-logs/${id}`),
  clear: (params) => http.delete('/operation-logs', { params })
}
