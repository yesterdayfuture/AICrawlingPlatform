<template>
  <div class="md-preview">
    <div class="md-toolbar">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button label="rendered">渲染预览</el-radio-button>
        <el-radio-button label="source">Markdown 源码</el-radio-button>
        <el-radio-button label="html">HTML 源码</el-radio-button>
      </el-radio-group>
      <el-button v-if="content" link type="primary" size="small" @click="copyContent">
        <el-icon><CopyDocument /></el-icon> 复制
      </el-button>
    </div>
    <div class="md-body">
      <div v-if="!content" class="md-empty">（无内容）</div>
      <div v-else-if="mode === 'rendered'" class="markdown-rendered" v-html="renderedHtml"></div>
      <pre v-else-if="mode === 'source'" class="markdown-source">{{ content }}</pre>
      <pre v-else class="markdown-html">{{ renderedHtml }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  content: { type: String, default: '' }
})

const mode = ref('rendered')

const renderedHtml = computed(() => {
  if (!props.content) return ''
  try {
    const raw = marked.parse(props.content, { breaks: true, gfm: true })
    return DOMPurify.sanitize(raw)
  } catch {
    return ''
  }
})

const copyContent = async () => {
  const text = mode.value === 'rendered' ? props.content : (mode.value === 'html' ? renderedHtml.value : props.content)
  try {
    await navigator.clipboard.writeText(text || '')
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择')
  }
}
</script>

<style scoped>
.md-preview { border: 1px solid var(--app-border-color); border-radius: 4px; overflow: hidden; background: var(--app-card-bg); }
.md-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--app-code-bg);
  border-bottom: 1px solid var(--app-border-color);
}
.md-body { max-height: 400px; overflow-y: auto; }
.md-empty { padding: 24px; color: var(--app-text-placeholder); text-align: center; }
.markdown-source, .markdown-html {
  margin: 0;
  padding: 12px 16px;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  line-height: 1.6;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
}
.markdown-rendered {
  padding: 16px 20px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.markdown-rendered :deep(h1) { font-size: 1.6em; margin: 0.6em 0 0.4em; border-bottom: 1px solid var(--app-border-color); padding-bottom: 0.3em; }
.markdown-rendered :deep(h2) { font-size: 1.4em; margin: 0.6em 0 0.4em; border-bottom: 1px solid var(--app-border-color); padding-bottom: 0.3em; }
.markdown-rendered :deep(h3) { font-size: 1.2em; margin: 0.6em 0 0.4em; }
.markdown-rendered :deep(h4) { font-size: 1.05em; margin: 0.6em 0 0.4em; }
.markdown-rendered :deep(p) { margin: 0.5em 0; }
.markdown-rendered :deep(ul), .markdown-rendered :deep(ol) { padding-left: 2em; margin: 0.5em 0; }
.markdown-rendered :deep(li) { margin: 0.2em 0; }
.markdown-rendered :deep(blockquote) { border-left: 4px solid var(--app-border-color); padding: 0.2em 1em; color: var(--app-text-secondary); margin: 0.6em 0; background: var(--app-code-bg); }
.markdown-rendered :deep(code) { background: var(--app-code-bg); padding: 2px 6px; border-radius: 3px; font-family: 'Menlo', 'Monaco', monospace; font-size: 0.9em; color: var(--app-accent); }
.markdown-rendered :deep(pre) { background: var(--app-code-bg); padding: 12px; border-radius: 4px; overflow-x: auto; margin: 0.6em 0; }
.markdown-rendered :deep(pre code) { background: none; padding: 0; color: var(--app-code-text); }
.markdown-rendered :deep(table) { border-collapse: collapse; width: 100%; margin: 0.6em 0; }
.markdown-rendered :deep(th), .markdown-rendered :deep(td) { border: 1px solid var(--app-border-color); padding: 6px 12px; text-align: left; }
.markdown-rendered :deep(th) { background: var(--app-code-bg); font-weight: 600; }
.markdown-rendered :deep(a) { color: #409eff; text-decoration: none; }
.markdown-rendered :deep(a:hover) { text-decoration: underline; }
.markdown-rendered :deep(img) { max-width: 100%; }
.markdown-rendered :deep(hr) { border: none; border-top: 1px solid var(--app-border-color); margin: 1em 0; }
</style>
