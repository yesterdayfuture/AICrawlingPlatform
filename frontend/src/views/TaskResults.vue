<template>
  <div>
    <div class="page-card">
      <SearchToolbar v-model="query" :status-options="statusOptions" @search="onSearch" @reset="onReset">
        <template #extra>
          <el-select v-model="query.task_id" placeholder="按任务过滤" clearable filterable style="width:200px" @change="onSearch">
            <el-option v-for="t in taskOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
          <el-button :icon="Download" @click="openExport">导出</el-button>
        </template>
      </SearchToolbar>
    </div>

    <div class="page-card">
      <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="task_name" label="所属任务" width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果统计" width="140">
          <template #default="{ row }">
            <span class="text-success">成功 {{ row.success_count }}</span> /
            <span class="text-failed">失败 {{ row.failed_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时(秒)" width="100">
          <template #default="{ row }">{{ row.duration?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="success" @click="openParse(row)">解析</el-button>
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

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="任务结果详情" size="60%">
      <div v-loading="detailLoading">
        <el-descriptions :column="2" border v-if="detail">
          <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="所属任务">{{ detail.task_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(detail.status)" size="small">{{ statusText(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ detail.duration?.toFixed(2) }} 秒</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(detail.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatTime(detail.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="成功/失败">{{ detail.success_count }} / {{ detail.failed_count }}</el-descriptions-item>
          <el-descriptions-item label="异常信息" :span="2">
            <span v-if="detail.error_message" class="text-failed mono">{{ detail.error_message }}</span>
            <span v-else>无</span>
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top:16px;font-weight:600">各地址抓取结果（{{ detail?.items?.length || 0 }}）</div>
        <el-collapse v-if="detail" style="margin-top:8px">
          <el-collapse-item v-for="item in detail.items" :key="item.id" :name="item.id">
            <template #title>
              <span style="display:flex;align-items:center;gap:8px;width:100%">
                <el-tag :type="item.success ? 'success' : 'danger'" size="small">{{ item.success ? '成功' : '失败' }}</el-tag>
                <span style="font-weight:600">{{ item.crawler_name }}</span>
                <span class="mono" style="color:var(--app-text-secondary);font-size:12px">{{ item.method }} {{ item.url }}</span>
                <span style="margin-left:auto;color:var(--app-text-secondary);font-size:12px">{{ item.duration?.toFixed(2) }}s · {{ item.status_code || '-' }}</span>
              </span>
            </template>
            <div v-if="!item.success" class="error-box mono">{{ item.error_message }}</div>
            <div class="content-box mono">{{ item.content || '(无内容)' }}</div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-drawer>

    <!-- 解析对话框 -->
    <el-dialog v-model="parseVisible" title="对原始结果进行解析" width="560px">
      <el-form ref="parseFormRef" :model="parseForm" :rules="parseRules" label-width="100px">
        <el-form-item label="解析名称" prop="name">
          <el-input v-model="parseForm.name" placeholder="如：新闻摘要解析" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="parseForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="选择大模型" prop="model_id">
          <el-select v-model="parseForm.model_id" placeholder="请选择" filterable style="width:100%">
            <el-option v-for="m in modelOptions" :key="m.id" :label="`${m.name} (${m.model_name})`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择提示词" prop="prompt_id">
          <el-select v-model="parseForm.prompt_id" placeholder="请选择" filterable style="width:100%">
            <el-option v-for="p in promptOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="解析范围">
          <el-radio-group v-model="parseAll">
            <el-radio :label="true">解析全部</el-radio>
            <el-radio :label="false">仅解析成功的</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="提取 API">
          <el-switch v-model="parseForm.extract_apis" />
          <span style="margin-left:8px;color:var(--app-text-secondary);font-size:12px">
            开启后将从原始文本中自动提取 API 接口信息（与提示词无关，内置功能）
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="parseVisible = false">取消</el-button>
        <el-button type="primary" :loading="parsing" @click="onParse">开始解析</el-button>
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
import { Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { taskResultApi, taskApi, modelApi, promptApi, buildListParams } from '@/api'
import SearchToolbar from '@/components/SearchToolbar.vue'
import ExportDialog from '@/components/ExportDialog.vue'

const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '部分成功', value: 'partial' },
  { label: '失败', value: 'failed' }
]
const statusType = (s) => ({ success: 'success', partial: 'warning', failed: 'danger' }[s] || 'info')
const statusText = (s) => ({ success: '成功', partial: '部分成功', failed: '失败' }[s] || s)

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, name: '', description: '', search_mode: 'fuzzy', status: '', task_id: undefined, start_time: undefined, end_time: undefined })
const taskOptions = ref([])

const formatTime = (t) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-')

const buildParams = () => {
  const p = buildListParams(query)
  if (query.task_id) p.task_id = query.task_id
  return p
}
const loadList = async () => {
  loading.value = true
  try {
    const data = await taskResultApi.list(buildParams())
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}
const loadTasks = async () => { taskOptions.value = (await taskApi.list({ page: 1, page_size: 200 })).items }
const onSearch = () => { query.page = 1; loadList() }
const onReset = () => { query.page = 1; loadList() }

// 详情
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const openDetail = async (row) => {
  detailVisible.value = true
  detailLoading.value = true
  try { detail.value = await taskResultApi.get(row.id) }
  finally { detailLoading.value = false }
}

// 解析
const parseVisible = ref(false)
const parsing = ref(false)
const parseFormRef = ref(null)
const modelOptions = ref([])
const promptOptions = ref([])
const parseAll = ref(true)
const parseForm = reactive({ task_result_id: null, name: '', description: '', model_id: null, prompt_id: null, extract_apis: false })
const parseRules = {
  name: [{ required: true, message: '请输入解析名称', trigger: 'blur' }],
  model_id: [{ required: true, message: '请选择大模型', trigger: 'change' }],
  prompt_id: [{ required: true, message: '请选择提示词', trigger: 'change' }]
}
const openParse = async (row) => {
  Object.assign(parseForm, { task_result_id: row.id, name: `${row.name} - 解析`, description: '', model_id: null, prompt_id: null, extract_apis: false })
  parseAll.value = true
  parseVisible.value = true
  const [ms, ps] = await Promise.all([modelApi.all(), promptApi.all()])
  modelOptions.value = ms
  promptOptions.value = ps
}
const onParse = async () => {
  await parseFormRef.value.validate()
  parsing.value = true
  const loading = ElLoading.service({ text: '正在调用大模型解析，请稍候...', background: 'rgba(0, 0, 0, 0.7)' })
  try {
    const data = await taskResultApi.parse(parseForm.task_result_id, parseForm)
    ElMessage.success(`解析完成，状态：${data.status}，解析ID：${data.parse_id}`)
    parseVisible.value = false
  } finally {
    loading.close()
    parsing.value = false
  }
}

const onRemove = async (row) => {
  await ElMessageBox.confirm(`确认删除任务结果「${row.name}」？`, '提示', { type: 'warning' })
  await taskResultApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}

// 导出
const selectedRows = ref([])
const onSelectionChange = (rows) => { selectedRows.value = rows }
const exportVisible = ref(false)
const exportFilename = ref('任务结果')
const openExport = () => { exportVisible.value = true }
const onExport = async ({ format, filename, ids, resolve, reject }) => {
  try {
    const result = await taskResultApi.export({ format, filename, query, ids })
    resolve(result)
  } catch (e) { reject(e) }
}

loadTasks()
loadList()
</script>

<style scoped>
.error-box { background: #fef0f0; color: #f56c6c; padding: 8px 12px; border-radius: 4px; margin-bottom: 8px; white-space: pre-wrap; word-break: break-all; }
.content-box { background: var(--app-code-bg); color: var(--app-code-text); padding: 8px 12px; border-radius: 4px; max-height: 400px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; font-size: 12px; }
</style>
