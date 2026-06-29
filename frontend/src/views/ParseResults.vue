<template>
  <div>
    <div class="page-card">
      <SearchToolbar v-model="query" :status-options="statusOptions" @search="onSearch" @reset="onReset">
        <template #extra>
          <el-select v-model="query.task_result_id" placeholder="按任务结果过滤" clearable filterable style="width:220px" @change="onSearch">
            <el-option v-for="t in taskResultOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
          <el-button :icon="Download" @click="openExport">导出</el-button>
        </template>
      </SearchToolbar>
    </div>

    <div class="page-card">
      <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="task_result_name" label="任务结果" width="160" show-overflow-tooltip />
        <el-table-column prop="model_name" label="模型" width="130" show-overflow-tooltip />
        <el-table-column prop="prompt_name" label="提示词" width="130" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Tokens(入/出/总)" width="150">
          <template #default="{ row }">{{ row.input_tokens }} / {{ row.output_tokens }} / {{ row.total_tokens }}</template>
        </el-table-column>
        <el-table-column prop="speed" label="速度(t/s)" width="100">
          <template #default="{ row }">{{ row.speed?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时(秒)" width="100">
          <template #default="{ row }">{{ row.duration?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
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
    <el-drawer v-model="detailVisible" title="解析结果详情" size="65%">
      <div v-loading="detailLoading">
        <el-descriptions :column="2" border v-if="detail">
          <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="任务结果">{{ detail.task_result_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ detail.model_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提示词">{{ detail.prompt_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detail.status === 'success' ? 'success' : 'danger'" size="small">
              {{ detail.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ detail.duration?.toFixed(2) }} 秒</el-descriptions-item>
          <el-descriptions-item label="输入 Tokens">{{ detail.input_tokens }}</el-descriptions-item>
          <el-descriptions-item label="输出 Tokens">{{ detail.output_tokens }}</el-descriptions-item>
          <el-descriptions-item label="总 Tokens">{{ detail.total_tokens }}</el-descriptions-item>
          <el-descriptions-item label="速度">{{ detail.speed?.toFixed(2) }} tokens/秒</el-descriptions-item>
          <el-descriptions-item label="异常信息" :span="2">
            <span v-if="detail.error_message" class="text-failed mono">{{ detail.error_message }}</span>
            <span v-else>无</span>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="detail" style="margin-top:16px">
          <div class="section-title"><span>解析结果</span></div>
          <Markdown-preview :content="detail.parsed_content || ''" />

          <!-- 提取到的 API 接口信息 -->
          <div class="section-title" style="margin-top:16px">
            <span>
              提取到的 API 接口
              <el-tag v-if="apiList.length" size="small" type="success" style="margin-left:6px">
                {{ apiList.length }} 个
              </el-tag>
              <el-tag
                v-else-if="detail.extract_apis_enabled"
                size="small"
                type="info"
                style="margin-left:6px"
              >
                已提取，未命中
              </el-tag>
              <el-tag v-else size="small" type="info" style="margin-left:6px">未启用</el-tag>
            </span>
            <el-button
              v-if="apiList.length"
              link
              type="primary"
              size="small"
              @click="copyText(JSON.stringify(apiList, null, 2))"
            >
              <el-icon><CopyDocument /></el-icon> 复制 JSON
            </el-button>
          </div>
          <el-empty
            v-if="!apiList.length && detail.extract_apis_enabled"
            description="已启用提取，但未从原始文本中提取到 API 接口信息"
            :image-size="60"
          />
          <el-alert
            v-else-if="!apiList.length && !detail.extract_apis_enabled"
            type="info"
            :closable="false"
            show-icon
            title="本次解析未启用 API 接口信息提取"
            description="发起解析时勾选「提取 API」即可在解析后自动从原始文本中提取 API 接口信息（与提示词无关，为内置功能）"
            style="margin:8px 0"
          />
          <el-table v-else :data="apiList" border stripe size="small">
            <el-table-column label="#" type="index" width="50" />
            <el-table-column label="方法" width="80">
              <template #default="{ row }">
                <el-tag
                  :type="methodTagType(row.method)"
                  size="small"
                  effect="dark"
                >
                  {{ row.method }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="URL / 路径" min-width="280">
              <template #default="{ row }">
                <div v-if="row.url" class="mono">{{ row.url }}</div>
                <div v-if="row.path && row.path !== row.url" class="mono" style="color:var(--app-text-secondary)">
                  路径: {{ row.path }}
                </div>
              </template>
            </el-table-column>
            <el-table-column label="查询参数" min-width="200">
              <template #default="{ row }">
                <div v-if="row.query_params && Object.keys(row.query_params).length">
                  <el-tag
                    v-for="(vals, key) in row.query_params"
                    :key="key"
                    size="small"
                    type="info"
                    style="margin:2px"
                  >
                    {{ key }}={{ vals.join(',') }}
                  </el-tag>
                </div>
                <span v-else style="color:var(--app-text-placeholder)">-</span>
              </template>
            </el-table-column>
            <el-table-column label="描述" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.description || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="来源" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="sourceTagType(row.source)">
                  {{ sourceLabel(row.source) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <div class="section-title" style="margin-top:16px">
            <span>原始输入</span>
            <el-button link type="primary" size="small" @click="copyText(detail.raw_input)">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
          <div class="content-box mono">{{ detail.raw_input || '(无)' }}</div>

          <div class="section-title" style="margin-top:16px">
            <span>原始输出</span>
            <el-button link type="primary" size="small" @click="copyText(detail.raw_output)">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
          <div class="content-box mono">{{ detail.raw_output || '(无)' }}</div>
        </div>
      </div>
    </el-drawer>

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
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { parseResultApi, taskResultApi, buildListParams } from '@/api'
import SearchToolbar from '@/components/SearchToolbar.vue'
import ExportDialog from '@/components/ExportDialog.vue'
import MarkdownPreview from '@/components/MarkdownPreview.vue'

const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' }
]

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, name: '', description: '', search_mode: 'fuzzy', status: '', task_result_id: undefined, start_time: undefined, end_time: undefined })
const taskResultOptions = ref([])

const formatTime = (t) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-')

const buildParams = () => {
  const p = buildListParams(query)
  if (query.task_result_id) p.task_result_id = query.task_result_id
  return p
}
const loadList = async () => {
  loading.value = true
  try {
    const data = await parseResultApi.list(buildParams())
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}
const loadTaskResults = async () => { taskResultOptions.value = (await taskResultApi.list({ page: 1, page_size: 200 })).items }
const onSearch = () => { query.page = 1; loadList() }
const onReset = () => { query.page = 1; loadList() }

// 详情
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const apiList = computed(() => {
  // 后端在详情接口已将 extracted_apis 解析为数组返回
  const v = detail.value?.extracted_apis
  return Array.isArray(v) ? v : []
})

// HTTP 方法对应的标签颜色
function methodTagType(method) {
  const m = (method || 'GET').toUpperCase()
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT' || m === 'PATCH') return 'warning'
  if (m === 'DELETE') return 'danger'
  return 'info'
}

// API 来源的标签颜色
function sourceTagType(source) {
  if (source === 'llm_json') return 'success'
  if (source === 'method_path') return 'warning'
  return 'info'
}

// API 来源的中文化
function sourceLabel(source) {
  if (source === 'llm_json') return '模型输出'
  if (source === 'method_path') return '方法声明'
  if (source === 'url') return 'URL'
  return source || '-'
}

const openDetail = async (row) => {
  detailVisible.value = true
  detailLoading.value = true
  try { detail.value = await parseResultApi.get(row.id) }
  finally { detailLoading.value = false }
}

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text || '')
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择')
  }
}

const onRemove = async (row) => {
  await ElMessageBox.confirm(`确认删除解析结果「${row.name}」？`, '提示', { type: 'warning' })
  await parseResultApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}

// 导出
const selectedRows = ref([])
const onSelectionChange = (rows) => { selectedRows.value = rows }
const exportVisible = ref(false)
const exportFilename = ref('解析结果')
const openExport = () => { exportVisible.value = true }
const onExport = async ({ format, filename, ids, resolve, reject }) => {
  try {
    const result = await parseResultApi.export({ format, filename, query, ids })
    resolve(result)
  } catch (e) { reject(e) }
}

loadTaskResults()
loadList()
</script>

<style scoped>
.section-title { display: flex; align-items: center; justify-content: space-between; font-weight: 600; margin-bottom: 8px; }
.content-box { background: var(--app-code-bg); padding: 10px 12px; border-radius: 4px; max-height: 320px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; font-size: 12px; line-height: 1.6; color: var(--app-code-text); }
</style>
