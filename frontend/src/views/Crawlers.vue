<template>
  <div>
    <div class="page-card">
      <SearchToolbar
        v-model="query"
        :status-options="statusOptions"
        @search="onSearch"
        @reset="onReset"
      >
        <template #extra>
          <el-button :icon="Download" @click="openExport">导出</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增爬虫</el-button>
        </template>
      </SearchToolbar>
    </div>

    <div class="page-card">
      <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column prop="method" label="方法" width="80">
          <template #default="{ row }">
            <el-tag :type="row.method === 'GET' ? 'success' : 'warning'" size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="url" label="URL" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small">
              {{ row.status === 'enabled' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="公开" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_public ? 'warning' : 'info'" size="small" effect="plain">
              {{ row.is_public ? '公开' : '私有' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑爬虫' : '新增爬虫'" width="720px" top="5vh">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：热门新闻列表" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="描述该爬虫的用途" />
        </el-form-item>
        <el-form-item label="请求方法" prop="method">
          <el-radio-group v-model="form.method">
            <el-radio-button label="GET" />
            <el-radio-button label="POST" />
          </el-radio-group>
        </el-form-item>
        <el-form-item label="URL" prop="url">
          <el-input v-model="form.url" placeholder="https://example.com/api/list" />
        </el-form-item>
        <el-form-item label="请求头">
          <el-input v-model="headersText" type="textarea" :rows="3" placeholder='JSON 格式，如 {"Authorization":"Bearer xxx","Content-Type":"application/json"}' />
          <div class="tip">
            <el-icon><InfoFilled /></el-icon>
            示例：
            <code>{"User-Agent":"Mozilla/5.0"}</code>，
            <code>{"Authorization":"Bearer token123"}</code>
          </div>
        </el-form-item>
        <el-form-item label="查询参数" v-if="form.method === 'GET' || form.method === 'POST'">
          <el-input v-model="paramsText" type="textarea" :rows="3" placeholder='JSON 格式，如 {"page":1,"size":20,"keyword":"AI"}' />
          <div class="tip">
            <el-icon><InfoFilled /></el-icon>
            示例：
            <code>{"page":1,"size":20}</code>，
            <code>{"category":"tech"}</code>
          </div>
        </el-form-item>
        <el-form-item label="请求体" v-if="form.method === 'POST'">
          <el-input v-model="bodyText" type="textarea" :rows="4" placeholder='POST 的 JSON body，如 {"title":"hello","content":"world"}' />
          <div class="tip">
            <el-icon><InfoFilled /></el-icon>
            示例：
            <code>{"query":"keyword","filters":{"date":"2024-01-01"}}</code>；留空则将查询参数作为表单提交
          </div>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio label="enabled">启用</el-radio>
            <el-radio label="disabled">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="是否公开">
          <el-switch v-model="form.is_public" />
          <span class="tip-inline">公开后所有用户可见可用，仅创建者可编辑/删除</span>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, InfoFilled, Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { crawlerApi, buildListParams } from '@/api'
import SearchToolbar from '@/components/SearchToolbar.vue'
import ExportDialog from '@/components/ExportDialog.vue'

const statusOptions = [
  { label: '启用', value: 'enabled' },
  { label: '禁用', value: 'disabled' }
]

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, name: '', description: '', search_mode: 'fuzzy', status: '', start_time: undefined, end_time: undefined })

const formatTime = (t) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-')

const loadList = async () => {
  loading.value = true
  try {
    const data = await crawlerApi.list(buildListParams(query))
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}
const onSearch = () => { query.page = 1; loadList() }
const onReset = () => { query.page = 1; loadList() }

// 表单
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const headersText = ref('{}')
const paramsText = ref('{}')
const bodyText = ref('{}')
const form = reactive({ id: null, name: '', description: '', method: 'GET', url: '', headers: {}, params: {}, body: {}, status: 'enabled', is_public: false })
const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入 URL', trigger: 'blur' }],
  method: [{ required: true, message: '请选择请求方法', trigger: 'change' }]
}

const parseJson = (text, field) => {
  try { return JSON.parse(text || '{}') } catch (e) {
    ElMessage.error(`${field} JSON 格式错误: ${e.message}`)
    return null
  }
}

const openCreate = () => {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', description: '', method: 'GET', url: '', headers: {}, params: {}, body: {}, status: 'enabled', is_public: false })
  headersText.value = '{}'
  paramsText.value = '{}'
  bodyText.value = '{}'
  dialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  Object.assign(form, JSON.parse(JSON.stringify(row)))
  headersText.value = JSON.stringify(form.headers || {}, null, 2)
  paramsText.value = JSON.stringify(form.params || {}, null, 2)
  bodyText.value = JSON.stringify(form.body || {}, null, 2)
  dialogVisible.value = true
}

const onSubmit = async () => {
  await formRef.value.validate()
  const headers = parseJson(headersText.value, '请求头')
  const params = parseJson(paramsText.value, '查询参数')
  const body = parseJson(bodyText.value, '请求体')
  if (headers === null || params === null || body === null) return
  form.headers = headers
  form.params = params
  form.body = body
  submitting.value = true
  try {
    if (isEdit.value) await crawlerApi.update(form.id, form)
    else await crawlerApi.create(form)
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadList()
  } finally {
    submitting.value = false
  }
}

const onRemove = async (row) => {
  await ElMessageBox.confirm(`确认删除爬虫「${row.name}」？`, '提示', { type: 'warning' })
  await crawlerApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}

// 导出
const selectedRows = ref([])
const onSelectionChange = (rows) => { selectedRows.value = rows }
const exportVisible = ref(false)
const exportFilename = ref('爬虫地址')
const openExport = () => { exportVisible.value = true }
const onExport = async ({ format, filename, ids, resolve, reject }) => {
  try {
    const result = await crawlerApi.export({ format, filename, query, ids })
    resolve(result)
  } catch (e) { reject(e) }
}

loadList()
</script>

<style scoped>
.tip { font-size: 12px; color: var(--app-text-secondary); margin-top: 4px; display: flex; align-items: center; gap: 4px; }
.tip code { background: var(--app-code-bg); padding: 1px 6px; border-radius: 3px; color: var(--app-accent); margin: 0 2px; }
.tip-inline { font-size: 12px; color: var(--app-text-secondary); margin-left: 12px; }
</style>
