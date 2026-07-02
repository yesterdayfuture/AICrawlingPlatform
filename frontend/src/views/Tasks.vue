<template>
  <div>
    <div class="page-card">
      <SearchToolbar v-model="query" :status-options="statusOptions" @search="onSearch" @reset="onReset">
        <template #extra>
          <el-button :icon="Download" @click="openExport">导出</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增任务</el-button>
        </template>
      </SearchToolbar>
    </div>

    <div class="page-card">
      <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column label="关联爬虫" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="n in row.crawler_names" :key="n" size="small" style="margin-right:4px;margin-bottom:4px">{{ n }}</el-tag>
            <span v-if="!row.crawler_names || !row.crawler_names.length" style="color:var(--app-text-placeholder)">未关联</span>
          </template>
        </el-table-column>
        <el-table-column label="定时" width="160">
          <template #default="{ row }">
            <el-tag v-if="row.is_scheduled" :type="scheduleTagType(row)" size="small">
              {{ scheduleText(row) }}
            </el-tag>
            <span v-else style="color:var(--app-text-placeholder)">手动</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small">
              {{ row.status === 'enabled' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_at" label="上次执行" width="170">
          <template #default="{ row }">{{ formatTime(row.last_run_at) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" :icon="VideoPlay" @click="onRun(row)">执行</el-button>
            <el-button v-if="canStartSchedule(row)" link type="primary" :icon="VideoPlay" @click="onStartSchedule(row)">启动定时</el-button>
            <el-button v-if="row.is_scheduled && row.status === 'enabled'" link type="warning" :icon="VideoPause" @click="onPauseSchedule(row)">暂停</el-button>
            <el-button v-if="row.is_scheduled" link type="danger" :icon="CircleClose" @click="onStopSchedule(row)">停止定时</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onRemove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-select v-model="query.page_size" style="width:110px;margin-right:12px" @change="onSearch">
          <el-option v-for="s in [10, 20, 50, 100]" :key="s" :label="`每页 ${s} 条`" :value="s" />
        </el-select>
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="loadList"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '新增任务'" width="680px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：每日新闻抓取" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="关联爬虫" prop="crawler_ids">
          <el-select
            v-model="form.crawler_ids"
            multiple
            filterable
            placeholder="可多选"
            style="width:100%"
          >
            <el-option v-for="c in crawlerOptions" :key="c.id" :label="`${c.name} (${c.method} ${c.url})`" :value="c.id" />
          </el-select>
          <div class="tip">
            <el-icon><InfoFilled /></el-icon>
            支持多选；执行任务时将依次请求所选爬虫地址
          </div>
        </el-form-item>
        <el-form-item label="是否定时">
          <el-switch v-model="form.is_scheduled" />
        </el-form-item>
        <el-form-item label="定时间隔" v-if="form.is_scheduled">
          <el-input-number v-model="form.interval_value" :min="1" :max="9999" />
          <el-select v-model="form.interval_unit" style="width:100px;margin-left:12px">
            <el-option label="分钟" value="min" />
            <el-option label="小时" value="hour" />
            <el-option label="天" value="day" />
            <el-option label="月" value="month" />
          </el-select>
          <div class="tip">
            <el-icon><InfoFilled /></el-icon>
            示例：每 30 分钟、每 6 小时、每 1 天、每 1 月
          </div>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio label="enabled">启用</el-radio>
            <el-radio label="disabled">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">确定</el-button>
      </template>
    </el-dialog>

    <ExportDialog
      v-model="exportVisible"
      :default-filename="exportFilename"
      :total="total"
      :has-selection="true"
      :selected-count="selectedRows.length"
      :selected-ids="selectedRows.map(r => r.id)"
      @confirm="onExport"
    />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Plus, InfoFilled, VideoPlay, VideoPause, CircleClose, Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { taskApi, crawlerApi, buildListParams } from '@/api'
import SearchToolbar from '@/components/SearchToolbar.vue'
import ExportDialog from '@/components/ExportDialog.vue'

const statusOptions = [
  { label: '启用', value: 'enabled' },
  { label: '禁用', value: 'disabled' }
]
const unitText = (u) => ({ min: '分钟', hour: '小时', day: '天', month: '月' }[u] || u)

// 调度状态显示
const scheduleText = (row) => {
  if (!row.is_scheduled) return '手动'
  const interval = `每 ${row.interval_value} ${unitText(row.interval_unit)}`
  return row.status === 'enabled' ? interval : `${interval}（已暂停）`
}
const scheduleTagType = (row) => {
  if (!row.is_scheduled) return 'info'
  return row.status === 'enabled' ? 'success' : 'warning'
}
// 启动定时按钮显示条件：未开启定时，或定时已暂停
const canStartSchedule = (row) => {
  return !row.is_scheduled || (row.is_scheduled && row.status !== 'enabled')
}

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, name: '', description: '', search_mode: 'fuzzy', status: '', start_time: undefined, end_time: undefined })
const crawlerOptions = ref([])

const formatTime = (t) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-')

const loadList = async () => {
  loading.value = true
  try {
    const data = await taskApi.list(buildListParams(query))
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}
const loadCrawlers = async () => { crawlerOptions.value = await crawlerApi.all() }
const onSearch = () => { query.page = 1; loadList() }
const onReset = () => { query.page = 1; loadList() }

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const form = reactive({ id: null, name: '', description: '', status: 'enabled', is_scheduled: false, interval_value: 30, interval_unit: 'min', crawler_ids: [] })
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  crawler_ids: [{ required: true, type: 'array', min: 1, message: '请至少选择一个爬虫', trigger: 'change' }]
}

const openCreate = () => {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', description: '', status: 'enabled', is_scheduled: false, interval_value: 30, interval_unit: 'min', crawler_ids: [] })
  dialogVisible.value = true
}
const openEdit = (row) => {
  isEdit.value = true
  Object.assign(form, JSON.parse(JSON.stringify(row)))
  dialogVisible.value = true
}
const onSubmit = async () => {
  await formRef.value.validate()
  if (form.is_scheduled && (!form.interval_value || form.interval_value < 1)) {
    ElMessage.warning('请填写有效的定时间隔'); return
  }
  submitting.value = true
  try {
    if (isEdit.value) await taskApi.update(form.id, form)
    else await taskApi.create(form)
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadList()
  } finally {
    submitting.value = false
  }
}
const onRemove = async (row) => {
  await ElMessageBox.confirm(`确认删除任务「${row.name}」？`, '提示', { type: 'warning' })
  await taskApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}
const onRun = async (row) => {
  await ElMessageBox.confirm(`确认立即执行任务「${row.name}」？`, '提示', { type: 'info' })
  const loading = ElLoading.service({ text: '任务执行中...', background: 'rgba(0, 0, 0, 0.7)' })
  try {
    const data = await taskApi.run(row.id)
    ElMessage.success(`执行完成，状态：${data.status}，结果ID：${data.result_id}`)
  } finally {
    loading.close()
  }
  loadList()
}

const onStartSchedule = async (row) => {
  await ElMessageBox.confirm(`确认启动任务「${row.name}」的定时调度？`, '提示', { type: 'info' })
  await taskApi.startSchedule(row.id)
  ElMessage.success('定时已启动')
  loadList()
}

const onPauseSchedule = async (row) => {
  await ElMessageBox.confirm(`确认暂停任务「${row.name}」的定时调度？`, '提示', { type: 'warning' })
  await taskApi.pauseSchedule(row.id)
  ElMessage.success('定时已暂停')
  loadList()
}

const onStopSchedule = async (row) => {
  await ElMessageBox.confirm(`确认停止任务「${row.name}」的定时调度？停止后将回到手动模式。`, '提示', { type: 'warning' })
  await taskApi.stopSchedule(row.id)
  ElMessage.success('定时已停止')
  loadList()
}

// 导出
const selectedRows = ref([])
const onSelectionChange = (rows) => { selectedRows.value = rows }
const exportVisible = ref(false)
const exportFilename = ref('任务')
const openExport = () => { exportVisible.value = true }
const onExport = async ({ format, filename, ids, resolve, reject }) => {
  try {
    const result = await taskApi.export({ format, filename, query, ids })
    resolve(result)
  } catch (e) { reject(e) }
}

loadCrawlers()
loadList()
</script>

<style scoped>
.tip { font-size: 12px; color: var(--app-text-secondary); margin-top: 4px; display: flex; align-items: center; gap: 4px; }
</style>
