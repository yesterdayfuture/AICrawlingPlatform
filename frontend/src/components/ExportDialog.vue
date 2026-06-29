<template>
  <el-dialog v-model="visible" title="导出数据" width="520px">
    <el-form :model="form" label-width="90px">
      <el-form-item label="文件名">
        <el-input v-model="form.filename" placeholder="请输入文件名（不含扩展名）">
          <template #append>
            <span>.{{ form.format }}</span>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item label="格式">
        <el-radio-group v-model="form.format">
          <el-radio-button label="xlsx">Excel</el-radio-button>
          <el-radio-button label="csv">CSV</el-radio-button>
          <el-radio-button label="json">JSON</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="保存地址">
        <el-input
          v-model="form.path"
          placeholder="留空则使用浏览器默认下载目录"
          clearable
        >
          <template #append>
            <el-button :icon="FolderOpened" @click="pickSavePath">选择</el-button>
          </template>
        </el-input>
        <div class="tip">
          <el-icon><InfoFilled /></el-icon>
          <span>支持 Chromium 内核浏览器（Chrome / Edge）选择保存位置；其他浏览器将使用默认下载目录</span>
        </div>
      </el-form-item>

      <el-form-item label="导出范围" v-if="hasSelection">
        <el-radio-group v-model="form.scope">
          <el-radio label="filtered">当前筛选结果（{{ total }} 条）</el-radio>
          <el-radio :label="'selected'">已选记录（{{ selectedCount }} 条）</el-radio>
        </el-radio-group>
        <div class="tip" v-if="form.scope === 'selected' && selectedCount === 0">
          <el-icon><WarningFilled /></el-icon>
          <span>请先在表格中勾选要导出的记录</span>
        </div>
      </el-form-item>
      <el-form-item label="导出范围" v-else>
        <span style="color:var(--app-text-secondary)">当前筛选结果（{{ total }} 条）</span>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="exporting" :disabled="!canExport" @click="onConfirm">导出</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened, InfoFilled, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // 默认文件名（不含扩展名）
  defaultFilename: { type: String, default: '导出数据' },
  // 当前筛选结果总数
  total: { type: Number, default: 0 },
  // 是否支持多选导出
  hasSelection: { type: Boolean, default: false },
  // 已选记录数
  selectedCount: { type: Number, default: 0 },
  // 已选记录 id 列表
  selectedIds: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const form = reactive({
  filename: props.defaultFilename,
  format: 'xlsx',
  path: '',
  scope: 'filtered'
})

watch(() => props.modelValue, (v) => {
  if (v) {
    form.filename = props.defaultFilename
    form.format = 'xlsx'
    form.path = ''
    form.scope = props.hasSelection && props.selectedCount > 0 ? 'selected' : 'filtered'
  }
})

const exporting = ref(false)
const canExport = computed(() => {
  if (form.scope === 'selected' && props.selectedCount === 0) return false
  return form.filename.trim().length > 0
})

const FORMAT_MIME = {
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  csv: 'text/csv',
  json: 'application/json'
}

const pickSavePath = async () => {
  // File System Access API：让用户选择保存位置
  if (!window.showSaveFilePicker) {
    ElMessage.info('当前浏览器不支持选择保存位置，将使用默认下载目录')
    return
  }
  const ext = form.format
  try {
    const handle = await window.showSaveFilePicker({
      suggestedName: `${form.filename || 'export'}.${ext}`,
      types: [{
        description: ext.toUpperCase(),
        accept: { [FORMAT_MIME[ext]]: [`.${ext}`] }
      }]
    })
    // 把用户选择的文件名（去扩展名）+ 路径名填回输入框
    form.filename = handle.name.replace(new RegExp(`\\.${ext}$`), '')
    // FileSystemFileHandle 没有完整路径 API，只能用 name 显示
    form.path = handle.name
    // 把 handle 暂存到 window 上，导出时直接写入
    window.__exportHandle = handle
  } catch (e) {
    if (e && e.name !== 'AbortError') {
      ElMessage.warning('选择保存位置失败：' + (e.message || e))
    }
  }
}

const onConfirm = async () => {
  if (!canExport.value) return
  exporting.value = true
  try {
    const opts = {
      format: form.format,
      filename: form.filename.trim(),
      ids: form.scope === 'selected' ? props.selectedIds : undefined
    }
    // emit 给父组件去发请求并传回 blob
    const result = await new Promise((resolve, reject) => {
      emit('confirm', { ...opts, resolve, reject })
    })
    await saveFile(result.blob, result.filename)
    ElMessage.success('导出成功')
    visible.value = false
  } catch (e) {
    ElMessage.error('导出失败：' + (e?.message || e))
  } finally {
    exporting.value = false
    window.__exportHandle = null
  }
}

async function saveFile(blob, fallbackName) {
  // 优先用 File System Access 写入用户选择的路径
  if (window.__exportHandle) {
    try {
      const w = await window.__exportHandle.createWritable()
      await w.write(blob)
      await w.close()
      return
    } catch (e) {
      // 写入失败则回退到普通下载
    }
  }
  // 回退：a 标签下载（无法选择保存位置）
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fallbackName || `${form.filename}.${form.format}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.tip {
  font-size: 12px;
  color: var(--app-text-secondary);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
  line-height: 1.4;
}
</style>
