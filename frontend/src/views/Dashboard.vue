<template>
  <div>
    <div class="page-card">
      <div class="toolbar">
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
        />
        <el-button type="primary" :icon="Search" @click="loadStats">查询统计</el-button>
        <div class="spacer"></div>
        <el-button :icon="Download" @click="openExport">导出统计</el-button>
        <span style="color:var(--app-text-secondary);font-size:13px">折线图最近</span>
        <el-input-number v-model="days" :min="1" :max="90" size="small" style="width:90px" />
        <span style="color:var(--app-text-secondary);font-size:13px">天</span>
        <el-button :icon="Refresh" @click="loadTrend">刷新趋势</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="6" v-for="card in cards" :key="card.key">
        <div class="stat-card" :style="{ background: card.bg }" @click="goTo(card.route)">
          <div class="stat-icon"><el-icon :size="32"><component :is="card.icon" /></el-icon></div>
          <div class="stat-body">
            <div class="stat-label">{{ card.label }}</div>
            <div class="stat-value">{{ stats[card.key] ?? 0 }}</div>
            <div class="stat-hint" v-if="card.hint">{{ card.hint }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top:16px">
      <div class="chart-header">
        <span class="chart-title">数据趋势</span>
      </div>
      <div ref="chartRef" style="width:100%;height:380px"></div>
    </div>

    <ExportDialog
      v-model="exportVisible"
      :default-filename="exportFilename"
      :total="1"
      @confirm="onExport"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Search, Refresh, Link, Cpu, ChatDotRound, List, Files, MagicStick, Download } from '@element-plus/icons-vue'
import { dashboardApi } from '@/api'
import { useThemeStore } from '@/store/theme'
import ExportDialog from '@/components/ExportDialog.vue'

const themeStore = useThemeStore()

const router = useRouter()
const timeRange = ref([])
const days = ref(7)
const stats = reactive({})
const chartRef = ref(null)
let chart = null

const cards = [
  { key: 'crawler_count', label: '爬虫地址', icon: Link, bg: 'linear-gradient(135deg,#667eea,#764ba2)', route: '/crawlers' },
  { key: 'model_count', label: '大模型', icon: Cpu, bg: 'linear-gradient(135deg,#43cea2,#185a9d)', route: '/models' },
  { key: 'prompt_count', label: '提示词', icon: ChatDotRound, bg: 'linear-gradient(135deg,#f093fb,#f5576c)', route: '/prompts' },
  { key: 'task_count', label: '任务', icon: List, bg: 'linear-gradient(135deg,#4facfe,#00f2fe)', route: '/tasks' },
  { key: 'task_result_count', label: '任务结果', icon: Files, bg: 'linear-gradient(135deg,#fa709a,#fee140)', route: '/task-results', hint: '点击查看详情' },
  { key: 'task_result_success', label: '成功结果', icon: Files, bg: 'linear-gradient(135deg,#43e97b,#38f9d7)', route: '/task-results' },
  { key: 'task_result_failed', label: '失败结果', icon: Files, bg: 'linear-gradient(135deg,#f5576c,#f093fb)', route: '/task-results' },
  { key: 'parse_result_count', label: '解析结果', icon: MagicStick, bg: 'linear-gradient(135deg,#a18cd1,#fbc2eb)', route: '/parse-results', hint: '点击查看解析' }
]

const goTo = (route) => router.push(route)

const loadStats = async () => {
  const params = {}
  if (timeRange.value && timeRange.value.length === 2) {
    params.start_time = timeRange.value[0]
    params.end_time = timeRange.value[1]
  }
  const data = await dashboardApi.stats(params)
  Object.assign(stats, data)
}

const trendData = ref(null)
const loadTrend = async () => {
  const data = await dashboardApi.trend({ days: days.value })
  trendData.value = data
  await nextTick()
  renderChart(data)
}

const renderChart = (data) => {
  if (!chart) chart = echarts.init(chartRef.value)
  const series = [
    { name: '爬虫', key: 'crawlers', color: '#667eea' },
    { name: '大模型', key: 'models', color: '#43cea2' },
    { name: '提示词', key: 'prompts', color: '#f5576c' },
    { name: '任务', key: 'tasks', color: '#4facfe' },
    { name: '任务结果', key: 'task_results', color: '#fa709a' },
    { name: '解析结果', key: 'parse_results', color: '#a18cd1' }
  ]
  // 跟随主题：暗色下文字/网格线使用浅色
  const isDark = themeStore.isDark.value
  const axisColor = isDark ? '#a3a6ad' : '#909399'
  const splitColor = isDark ? '#303030' : '#ebeef5'
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: series.map((s) => s.name), bottom: 0, textStyle: { color: axisColor } },
    grid: { left: 40, right: 30, top: 30, bottom: 50 },
    xAxis: {
      type: 'category', data: data.dates, boundaryGap: false,
      axisLine: { lineStyle: { color: splitColor } },
      axisLabel: { color: axisColor },
      splitLine: { lineStyle: { color: splitColor } }
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLine: { lineStyle: { color: splitColor } },
      axisLabel: { color: axisColor },
      splitLine: { lineStyle: { color: splitColor } }
    },
    series: series.map((s) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      data: data[s.key] || [],
      itemStyle: { color: s.color }
    }))
  })
}

const onResize = () => chart && chart.resize()

// 导出
const exportVisible = ref(false)
const exportFilename = ref('总览统计')
const openExport = () => { exportVisible.value = true }
const onExport = async ({ format, filename, resolve, reject }) => {
  try {
    const query = {
      start_time: timeRange.value?.[0] || undefined,
      end_time: timeRange.value?.[1] || undefined
    }
    const result = await dashboardApi.export({ format, filename, query })
    resolve(result)
  } catch (e) { reject(e) }
}

onMounted(async () => {
  await loadStats()
  await loadTrend()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart && chart.dispose()
})

// 主题切换时重绘图表
watch(() => themeStore.isDark.value, async () => {
  if (chart && trendData.value) {
    await nextTick()
    renderChart(trendData.value)
  }
})
</script>

<style scoped>
.stat-card {
  border-radius: 8px;
  padding: 20px;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  margin-bottom: 16px;
  height: 120px;          /* 固定高度，避免有无 hint 导致卡片高度不一致 */
  box-sizing: border-box;
}
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
.stat-icon { opacity: 0.9; flex-shrink: 0; }
.stat-body { flex: 1; min-width: 0; }
.stat-label { font-size: 13px; opacity: 0.9; }
.stat-value { font-size: 28px; font-weight: 700; margin-top: 4px; line-height: 1.2; }
.stat-hint { font-size: 11px; opacity: 0.8; margin-top: 4px; min-height: 14px; }
.chart-header { display: flex; align-items: center; margin-bottom: 12px; }
.chart-title { font-size: 16px; font-weight: 600; }
</style>
