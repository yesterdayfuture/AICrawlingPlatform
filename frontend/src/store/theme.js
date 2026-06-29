import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'app-theme'
const LIGHT = 'light'
const DARK = 'dark'

function applyTheme(theme) {
  const html = document.documentElement
  if (theme === DARK) {
    html.classList.add('dark')
  } else {
    html.classList.remove('dark')
  }
}

function loadInitial() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === LIGHT || saved === DARK) return saved
  // 首次访问跟随系统偏好
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    ? DARK
    : LIGHT
}

export const useThemeStore = defineStore('theme', () => {
  const current = ref(loadInitial())

  // 初始化时立即应用
  applyTheme(current.value)

  const isDark = computed(() => current.value === DARK)

  function setTheme(theme) {
    current.value = theme
    applyTheme(theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }

  function toggle() {
    setTheme(current.value === DARK ? LIGHT : DARK)
  }

  return { current, isDark, setTheme, toggle }
})
