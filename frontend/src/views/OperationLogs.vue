<template>
  <div>
    <!-- 搜索栏 -->
    <div class="page-card">
      <div class="logs-toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="关键词：用户名/模块/动作/路径"
          clearable
          style="width: 260px"
          @keyup.enter="onSearch"
        />
        <el-select v-model="query.search_mode" style="width: 110px">
          <el-option label="模糊查询" value="fuzzy" />
          <el-option label="精准查询" value="exact" />
        </el-select>
        <el-select v-model="query.username" placeholder="按用户名筛选" clearable filterable allow-create style="width: 180px" @change="onSearch">
          <el-option v-for="u in filterOptions.usernames" :key="u" :label="u" :value="u" />
        </el-select>
        <el-select v-model="query.module" placeholder="按模块筛选" clearable filterable style="width: 160px" @change="onSearch">
          <el-option v-for="m in filterOptions.modules" :key="m" :label="m" :value="m" />
        </el-select>
        <el-select v-model="query.action" placeholder="按动作筛选" clearable filterable style="width: 160px" @change="onSearch">
          <el-option v-for="a in filterOptions.actions" :key="a" :label="a" :value="a" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="onSearch">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 360px"
          @change="onSearch"
        />
        <el-button type="primary" :icon="Search" @click="onSearch">查询</el-button>
        <el-button :icon="Refresh" @click="onReset">重置</el-button>
        <div class="spacer"></div>
        <el-button type="danger" :icon="Delete" plain @click="openClearDialog">清空日志</el-button>
      </div>
    </div>

    <!-- 日志表格 -->
    <div class="page-card">
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户" width="130" show-overflow-tooltip />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="action" label="动作" width="120" />
        <el-table-column prop="method" label="方法" width="80">
          <template #default="{ row }">
            <el-tag :type="methodTagType(row.method)" size="small" effect="plain">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="请求路径" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_code" label="状态码" width="80" />
        <el-table-column prop="ip" label="IP" width="130" show-overflow-tooltip />
        <el-table-column prop="duration_ms" label="耗时(ms)" width="90" />
        <el-table-column prop="created_at" label="操作时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="danger" @click="onRemove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-select v-model="query.page_size" style="width:110px;margin-right:12px" @change="onSearch">
          <el-option v-for="s in [10, 20, 50, 100, 200]" :key="s" :label="`每页 ${s} 条`" :value="s" />
        </el-select>
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100, 200]"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="loadList"
        />
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="日志详情" size="50%">
      <div v-if="currentLog" class="log-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ currentLog.id }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ currentLog.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="用户ID">{{ currentLog.user_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="模块">{{ currentLog.module || '-' }}</el-descriptions-item>
          <el-descriptions-item label="动作">{{ currentLog.action || '-' }}</el-descriptions-item>
          <el-descriptions-item label="HTTP方法">{{ currentLog.method || '-' }}</el-descriptions-item>
          <el-descriptions-item label="请求路径">{{ currentLog.path || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentLog.status === 'success' ? 'success' : 'danger'" size="small">
              {{ currentLog.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态码">{{ currentLog.status_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="耗时(ms)">{{ currentLog.duration_ms || 0 }}</el-descriptions-item>
          <el-descriptions-item label="IP">{{ currentLog.ip || '-' }}</el-descriptions-item>
          <el-descriptions-item label="操作时间">{{ currentLog.created_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="User-Agent" :span="2">{{ currentLog.user_agent || '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误信息" :span="2">
            <span v-if="currentLog.error_msg" class="error-msg">{{ currentLog.error_msg }}</span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="请求参数" :span="2">
            <pre v-if="currentLog.params" class="params-box">{{ formatParams(currentLog.params) }}</pre>
            <span v-else>-</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>

    <!-- 清空日志对话框 -->
    <el-dialog v-model="clearDialogVisible" title="清空日志" width="440px">
      <el-form label-width="100px">
        <el-form-item label="清理范围">
          <el-radio-group v-model="clearForm.before_days">
            <el-radio :value="0">清空全部</el-radio>
            <el-radio :value="7">7 天前</el-radio>
            <el-radio :value="30">30 天前</el-radio>
            <el-radio :value="90">90 天前</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="clearDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="clearLoading" @click="onClear">确认清空</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Delete } from '@element-plus/icons-vue'
import { operationLogApi } from '@/api'

const list = ref([])
const total = ref(0)
const loading = ref(false)

const query = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  search_mode: 'fuzzy',
  username: '',
  module: '',
  action: '',
  status: '',
  start_time: undefined,
  end_time: undefined
})

const timeRange = ref([])
const filterOptions = ref({ modules: [], actions: [], usernames: [] })

const detailVisible = ref(false)
const currentLog = ref(null)

const clearDialogVisible = ref(false)
const clearLoading = ref(false)
const clearForm = reactive({ before_days: 0 })

function buildParams() {
  const p = { page: query.page, page_size: query.page_size, search_mode: query.search_mode }
  if (query.keyword) p.keyword = query.keyword
  if (query.username) p.username = query.username
  if (query.module) p.module = query.module
  if (query.action) p.action = query.action
  if (query.status) p.status = query.status
  if (timeRange.value && timeRange.value.length === 2) {
    p.start_time = timeRange.value[0]
    p.end_time = timeRange.value[1]
  }
  return p
}

async function loadList() {
  loading.value = true
  try {
    const data = await operationLogApi.list(buildParams())
    list.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

async function loadFilters() {
  try {
    const data = await operationLogApi.filters()
    filterOptions.value = data || { modules: [], actions: [], usernames: [] }
  } catch (e) {
    // 忽略
  }
}

function onSearch() {
  query.page = 1
  loadList()
}

function onReset() {
  query.keyword = ''
  query.search_mode = 'fuzzy'
  query.username = ''
  query.module = ''
  query.action = ''
  query.status = ''
  timeRange.value = []
  query.page = 1
  loadList()
}

function methodTagType(method) {
  const map = { GET: 'info', POST: 'success', PUT: 'warning', DELETE: 'danger' }
  return map[method] || 'info'
}

async function openDetail(row) {
  currentLog.value = row
  detailVisible.value = true
}

function formatParams(paramsStr) {
  try {
    return JSON.stringify(JSON.parse(paramsStr), null, 2)
  } catch {
    return paramsStr
  }
}

async function onRemove(row) {
  try {
    await ElMessageBox.confirm(`确认删除日志 #${row.id}？`, '提示', { type: 'warning' })
    await operationLogApi.remove(row.id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

function openClearDialog() {
  clearForm.before_days = 0
  clearDialogVisible.value = true
}

async function onClear() {
  clearLoading.value = true
  try {
    const data = await operationLogApi.clear({ before_days: clearForm.before_days })
    ElMessage.success(`已清理 ${data.deleted} 条日志`)
    clearDialogVisible.value = false
    loadList()
    loadFilters()
  } catch (e) {
    ElMessage.error('清空失败')
  } finally {
    clearLoading.value = false
  }
}

onMounted(() => {
  loadFilters()
  loadList()
})
</script>

<style scoped>
.logs-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.logs-toolbar .spacer {
  flex: 1;
}
.log-detail {
  padding: 0 12px;
}
.params-box {
  background: var(--app-code-bg);
  color: var(--app-code-text);
  padding: 10px;
  border-radius: 4px;
  font-family: 'Menlo', 'Monaco', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  max-height: 240px;
  overflow: auto;
}
.error-msg {
  color: #f56c6c;
  word-break: break-all;
}
.pagination-wrap {
  display: flex;
  align-items: center;
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
