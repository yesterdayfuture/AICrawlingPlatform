<template>
  <div class="toolbar">
    <el-input
      v-model="local.name"
      placeholder="按名称搜索"
      clearable
      style="width: 180px"
      @keyup.enter="$emit('search')"
    />
    <el-input
      v-model="local.description"
      placeholder="按描述搜索"
      clearable
      style="width: 180px"
      @keyup.enter="$emit('search')"
    />
    <el-select v-model="local.search_mode" style="width: 110px">
      <el-option label="模糊查询" value="fuzzy" />
      <el-option label="精准查询" value="exact" />
    </el-select>
    <el-select v-model="local.status" placeholder="状态" clearable style="width: 130px">
      <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
    </el-select>
    <el-date-picker
      v-model="timeRange"
      type="datetimerange"
      range-separator="至"
      start-placeholder="开始时间"
      end-placeholder="结束时间"
      value-format="YYYY-MM-DDTHH:mm:ss"
      style="width: 360px"
    />
    <el-button type="primary" :icon="Search" @click="$emit('search')">查询</el-button>
    <el-button :icon="Refresh" @click="onReset">重置</el-button>
    <div class="spacer"></div>
    <slot name="extra" />
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  statusOptions: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue', 'search', 'reset'])

const local = reactive({ ...props.modelValue })
const timeRange = ref([])

watch(
  () => props.modelValue,
  (v) => Object.assign(local, v),
  { deep: true }
)

watch(timeRange, (val) => {
  local.start_time = val && val.length === 2 ? val[0] : undefined
  local.end_time = val && val.length === 2 ? val[1] : undefined
})

watch(
  local,
  (v) => emit('update:modelValue', { ...v }),
  { deep: true }
)

const onReset = () => {
  local.name = ''
  local.description = ''
  local.search_mode = 'fuzzy'
  local.status = ''
  local.start_time = undefined
  local.end_time = undefined
  timeRange.value = []
  emit('reset')
}
</script>
