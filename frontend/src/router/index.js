import { createRouter, createWebHistory } from 'vue-router'
import { userStore } from '@/store/user'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { title: '登录', public: true } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '总览' } },
  { path: '/crawlers', name: 'Crawlers', component: () => import('@/views/Crawlers.vue'), meta: { title: '爬虫地址' } },
  { path: '/models', name: 'Models', component: () => import('@/views/Models.vue'), meta: { title: '大模型管理' } },
  { path: '/prompts', name: 'Prompts', component: () => import('@/views/Prompts.vue'), meta: { title: '提示词管理' } },
  { path: '/tasks', name: 'Tasks', component: () => import('@/views/Tasks.vue'), meta: { title: '任务中心' } },
  { path: '/task-results', name: 'TaskResults', component: () => import('@/views/TaskResults.vue'), meta: { title: '任务结果' } },
  { path: '/parse-results', name: 'ParseResults', component: () => import('@/views/ParseResults.vue'), meta: { title: '解析结果' } },
  {
    path: '/users',
    name: 'Users',
    component: () => import('@/views/Users.vue'),
    meta: { title: '用户管理', requireAdmin: true }
  },
  {
    path: '/operation-logs',
    name: 'OperationLogs',
    component: () => import('@/views/OperationLogs.vue'),
    meta: { title: '操作日志', requireAdmin: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { title: '个人中心' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 公开路由直接放行
  if (to.meta.public) {
    // 已登录用户访问登录页，跳转首页
    if (to.name === 'Login' && userStore.isLogin.value) {
      return next('/dashboard')
    }
    return next()
  }
  // 未登录跳登录页
  if (!userStore.isLogin.value) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  // 需要管理员权限
  if (to.meta.requireAdmin && !userStore.isAdmin.value) {
    return next('/dashboard')
  }
  next()
})

export default router
