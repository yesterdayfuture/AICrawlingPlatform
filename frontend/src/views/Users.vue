<template>
  <div class="page">
    <!-- 搜索工具栏 -->
    <el-card class="search-card" shadow="never">
      <SearchToolbar
        v-model:query="query"
        :search="loadList"
        :reset="resetQuery"
        :show-status="true"
        :status-options="statusOptions"
      >
        <template #extra>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增用户</el-button>
        </template>
      </SearchToolbar>
    </el-card>

    <!-- 列表 -->
    <el-card class="table-card" shadow="never">
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="nickname" label="昵称" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'warning'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最近登录" width="170">
          <template #default="{ row }">{{ formatTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              link
              :type="row.is_active ? 'warning' : 'success'"
              size="small"
              :disabled="row.id === currentUserId"
              @click="onToggle(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.id === currentUserId"
              @click="onDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="loadList"
          @size-change="loadList"
        />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增用户' : '编辑用户'"
      width="520px"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item v-if="dialogMode === 'create'" label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="显示昵称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="可选" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item v-else label="状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'edit'" label="重置密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="留空则不修改密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import SearchToolbar from '@/components/SearchToolbar.vue'
import { userApi } from '@/api'
import { userStore } from '@/store/user'

const currentUserId = computed(() => userStore.state.user?.id)

const query = reactive({
  page: 1,
  page_size: 10,
  name: '',
  status: ''
})
const statusOptions = [
  { label: '启用', value: 'active' },
  { label: '禁用', value: 'disabled' }
]

const list = ref([])
const total = ref(0)
const loading = ref(false)

async function loadList() {
  loading.value = true
  try {
    const params = {
      page: query.page,
      page_size: query.page_size,
      name: query.name || undefined,
      status: query.status || undefined
    }
    const data = await userApi.list(params)
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.page = 1
  query.page_size = 10
  query.name = ''
  query.status = ''
  loadList()
}

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

// ============ 新增/编辑 ============
const dialogVisible = ref(false)
const dialogMode = ref('create')
const saving = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  username: '',
  nickname: '',
  email: '',
  role: 'user',
  password: '',
  is_active: true
})

const formRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    {
      validator: (rule, val, cb) => {
        if (dialogMode.value === 'edit' && !val) return cb()  // 编辑时可不改
        if (!val) return cb(new Error('请输入密码'))
        if (val.length < 6) return cb(new Error('密码至少 6 位'))
        cb()
      },
      trigger: 'blur'
    }
  ]
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, {
    id: null, username: '', nickname: '', email: '',
    role: 'user', password: '', is_active: true
  })
  dialogVisible.value = true
}

function openEdit(row) {
  dialogMode.value = 'edit'
  Object.assign(form, {
    id: row.id,
    username: row.username,
    nickname: row.nickname || '',
    email: row.email || '',
    role: row.role,
    password: '',
    is_active: row.is_active
  })
  dialogVisible.value = true
}

async function onSave() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload = {
      nickname: form.nickname,
      email: form.email,
      role: form.role
    }
    if (dialogMode.value === 'create') {
      payload.username = form.username
      payload.password = form.password
      await userApi.create(payload)
      ElMessage.success('创建成功')
    } else {
      payload.is_active = form.is_active
      if (form.password) payload.password = form.password
      await userApi.update(form.id, payload)
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadList()
  } finally {
    saving.value = false
  }
}

async function onToggle(row) {
  try {
    await userApi.toggleStatus(row.id)
    ElMessage.success('状态已更新')
    loadList()
  } catch {}
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除用户「${row.username}」？该用户创建的数据将一并删除。`,
      '危险操作',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await userApi.remove(row.id)
    ElMessage.success('删除成功')
    loadList()
  } catch {}
}

onMounted(loadList)
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.search-card :deep(.el-card__body) { padding: 12px 16px; }
.table-card :deep(.el-card__body) { padding: 12px; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
</style>
