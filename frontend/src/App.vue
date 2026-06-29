<template>
  <!-- 公开路由（登录页等）独立渲染，不带主框架布局 -->
  <router-view v-if="isPublicRoute" />
  <el-container v-else class="app-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="app-aside">
      <div class="logo">
        <el-icon :size="22"><Cpu /></el-icon>
        <span v-show="!isCollapse" class="logo-text">智能爬取系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        router
        :background-color="asideBg"
        :text-color="asideText"
        :active-text-color="asideActive"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <template #title>总览</template>
        </el-menu-item>
        <el-menu-item index="/crawlers">
          <el-icon><Link /></el-icon>
          <template #title>爬虫地址</template>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Cpu /></el-icon>
          <template #title>大模型管理</template>
        </el-menu-item>
        <el-menu-item index="/prompts">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>提示词管理</template>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <template #title>任务中心</template>
        </el-menu-item>
        <el-menu-item index="/task-results">
          <el-icon><Files /></el-icon>
          <template #title>任务结果</template>
        </el-menu-item>
        <el-menu-item index="/parse-results">
          <el-icon><MagicStick /></el-icon>
          <template #title>解析结果</template>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/users">
          <el-icon><UserFilled /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/operation-logs">
          <el-icon><Document /></el-icon>
          <template #title>操作日志</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
        </el-breadcrumb>

        <div class="header-right">
          <el-icon class="theme-btn" :size="18" @click="themeStore.toggle()">
            <Sunny v-if="themeStore.isDark.value" />
            <Moon v-else />
          </el-icon>
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-info">
              <el-avatar :size="28" class="user-avatar">
                {{ avatarText }}
              </el-avatar>
              <span class="user-name">{{ displayName }}</span>
              <el-tag v-if="isAdmin" type="danger" size="small" effect="dark">管理员</el-tag>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人中心
                </el-dropdown-item>
                <el-dropdown-item v-if="isAdmin" command="users">
                  <el-icon><UserFilled /></el-icon> 用户管理
                </el-dropdown-item>
                <el-dropdown-item v-if="isAdmin" command="logs">
                  <el-icon><Document /></el-icon> 操作日志
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Cpu, DataLine, Link, ChatDotRound, List, Files, MagicStick,
  UserFilled, User, ArrowDown, SwitchButton, Fold, Expand, Document,
  Sunny, Moon,
} from '@element-plus/icons-vue'
import { userStore } from '@/store/user'
import { useThemeStore } from '@/store/theme'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const activeMenu = computed(() => route.path)
const isPublicRoute = computed(() => route.meta.public === true)

const themeStore = useThemeStore()
// 侧边栏颜色跟随主题（el-menu 需要字符串色值）
const asideBg = computed(() => themeStore.isDark.value ? '#1d1e1f' : '#001529')
const asideText = computed(() => themeStore.isDark.value ? '#c9d1d9' : '#b7bdc6')
const asideActive = computed(() => themeStore.isDark.value ? '#ffd04b' : '#fff')

const isAdmin = computed(() => userStore.isAdmin.value)
const displayName = computed(() => userStore.username.value)
const avatarText = computed(() => {
  const name = userStore.state.user?.nickname || userStore.state.user?.username || '?'
  return name.charAt(0).toUpperCase()
})

const titleMap = {
  '/dashboard': '总览',
  '/crawlers': '爬虫地址管理',
  '/models': '大模型信息管理',
  '/prompts': '提示词信息管理',
  '/tasks': '任务中心',
  '/task-results': '任务执行结果管理',
  '/parse-results': '解析结果管理',
  '/users': '用户管理',
  '/operation-logs': '操作日志',
  '/profile': '个人中心'
}
const currentTitle = computed(() => titleMap[route.path] || '')

// 启动时拉取最新用户信息（页面刷新后恢复用户状态）
onMounted(async () => {
  if (userStore.isLogin.value) {
    await userStore.fetchMe()
  }
})

async function onCommand(cmd) {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'users') {
    router.push('/users')
  } else if (cmd === 'logs') {
    router.push('/operation-logs')
  } else if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确认退出登录？', '提示', {
        type: 'warning',
        confirmButtonText: '退出',
        cancelButtonText: '取消'
      })
    } catch {
      return
    }
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-container { height: 100vh; }
.app-aside {
  background: var(--app-aside-bg);
  transition: width 0.28s, background-color 0.3s;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid var(--app-aside-border);
}
.logo-text { white-space: nowrap; }
.app-aside :deep(.el-menu) {
  border-right: none;
  flex: 1;
  background-color: var(--app-aside-bg) !important;
}
/* 菜单项 hover/active 背景与侧边栏协调，避免 Element Plus 默认浅蓝突兀 */
.app-aside :deep(.el-menu-item),
.app-aside :deep(.el-sub-menu__title) {
  background-color: transparent !important;
}
.app-aside :deep(.el-menu-item:hover),
.app-aside :deep(.el-sub-menu__title:hover) {
  background-color: var(--app-aside-hover-bg) !important;
}
.app-aside :deep(.el-menu-item.is-active) {
  background-color: var(--app-aside-active-bg) !important;
  color: var(--app-aside-active) !important;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--app-header-bg);
  border-bottom: 1px solid var(--app-header-border);
  transition: background-color 0.3s, border-color 0.3s;
}
.collapse-btn { cursor: pointer; font-size: 20px; color: var(--app-text); }
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}
.theme-btn {
  cursor: pointer;
  color: var(--app-text);
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.3s;
}
.theme-btn:hover { background: var(--app-hover-bg); }
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
  padding: 4px 8px;
  border-radius: 4px;
}
.user-info:hover { background: var(--app-hover-bg); }
.user-avatar {
  background: #409EFF;
  color: #fff;
  font-weight: 600;
}
.user-name {
  font-size: 14px;
  color: var(--app-text);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.app-main {
  background: var(--app-bg);
  padding: 16px;
  overflow-y: auto;
  transition: background-color 0.3s;
}
</style>
