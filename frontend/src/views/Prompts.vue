<template>
  <div>
    <div class="page-card">
      <SearchToolbar v-model="query" :status-options="statusOptions" @search="onSearch" @reset="onReset">
        <template #extra>
          <el-button :icon="Download" @click="openExport">导出</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增提示词</el-button>
        </template>
      </SearchToolbar>
    </div>

    <div class="page-card">
      <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
        <el-table-column prop="system_prompt" label="System Prompt" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono">{{ (row.system_prompt || '').slice(0, 80) }}{{ (row.system_prompt || '').length > 80 ? '...' : '' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_prompt" label="User Prompt" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono">{{ (row.user_prompt || '').slice(0, 80) }}{{ (row.user_prompt || '').length > 80 ? '...' : '' }}</span>
          </template>
        </el-table-column>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑提示词' : '新增提示词'" width="720px" top="5vh">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：新闻内容摘要提取" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="System Prompt">
          <el-input v-model="form.system_prompt" type="textarea" :rows="5" placeholder="设定模型角色，如：你是一个信息抽取助手，请从给定的网页内容中提取结构化信息。" />
        </el-form-item>
        <el-form-item label="User Prompt">
          <el-input v-model="form.user_prompt" type="textarea" :rows="7" placeholder="可使用占位符 {content} 表示待解析内容；不填则系统自动拼接。" />
          <div class="tip">
            <el-icon><InfoFilled /></el-icon>
            示例：<code>请从以下内容中提取标题、作者、发布时间，并以 JSON 返回：{"title":"","author":"","date":""}</code>
            <br />可用 <code>{'{'}</code><code>content}</code> 占位符引用爬虫抓取的原始内容
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
import { promptApi, buildListParams } from '@/api'
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
    const data = await promptApi.list(buildListParams(query))
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}
const onSearch = () => { query.page = 1; loadList() }
const onReset = () => { query.page = 1; loadList() }

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const form = reactive({ id: null, name: '', description: '', system_prompt: '', user_prompt: '', status: 'enabled', is_public: false })
const rules = { name: [{ required: true, message: '请输入名称', trigger: 'blur' }] }

const openCreate = () => {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', description: '', system_prompt: '', user_prompt: '', status: 'enabled', is_public: false })
  dialogVisible.value = true
}
const openEdit = (row) => {
  isEdit.value = true
  Object.assign(form, JSON.parse(JSON.stringify(row)))
  dialogVisible.value = true
}
const onSubmit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value) await promptApi.update(form.id, form)
    else await promptApi.create(form)
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadList()
  } finally {
    submitting.value = false
  }
}
const onRemove = async (row) => {
  await ElMessageBox.confirm(`确认删除提示词「${row.name}」？`, '提示', { type: 'warning' })
  await promptApi.remove(row.id)
  ElMessage.success('删除成功')
  loadList()
}

// 导出
const selectedRows = ref([])
const onSelectionChange = (rows) => { selectedRows.value = rows }
const exportVisible = ref(false)
const exportFilename = ref('提示词信息')
const openExport = () => { exportVisible.value = true }
const onExport = async ({ format, filename, ids, resolve, reject }) => {
  try {
    const result = await promptApi.export({ format, filename, query, ids })
    resolve(result)
  } catch (e) { reject(e) }
}

loadList()
</script>

<style scoped>
.tip { font-size: 12px; color: var(--app-text-secondary); margin-top: 4px; line-height: 1.6; }
.tip code { background: var(--app-code-bg); padding: 1px 6px; border-radius: 3px; color: var(--app-accent); }
.tip-inline { font-size: 12px; color: var(--app-text-secondary); margin-left: 12px; }
</style>
