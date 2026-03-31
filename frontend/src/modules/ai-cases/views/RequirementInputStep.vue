<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import type { Platform, TaskFormState } from '../types'
import { createWorkflowApi } from '../api'

const props = defineProps<{
  form: TaskFormState
  platforms: { label: string; value: Platform; description: string }[]
  projects: { label: string; value: string }[]
  loading: boolean
  uploadingPdf: boolean
  pdfFileName: string
  apiBaseUrl: string
  sourceTitle: string
  sourceImages: { index: number; data_url: string; context: string }[]
  sourceType: string
}>()

const emit = defineEmits<{
  submit: []
  uploadPdf: [file: File]
  importFeishu: [payload: { title: string; markdown: string; images: typeof props.sourceImages; url: string; sourceType: string }]
  clearImportedSource: []
}>()

const api = createWorkflowApi(props.apiBaseUrl)
const showFeishuInput = ref(false)
const feishuUrl = ref('')
const feishuLoading = ref(false)
const feishuError = ref('')

const hasContent = computed(() => props.form.requirementText.trim().length > 0)

// 预览 HTML：图片占位符替换回实际图片
const renderedPreviewHtml = computed(() => {
  let md = props.form.requirementText
  if (!md) return '<p style="color:var(--text-faint);text-align:center;padding:40px 0">编辑区输入内容后，这里会实时预览</p>'
  for (const img of props.sourceImages) {
    md = md.replace(`[图片${img.index}]`, `![图片${img.index}](${img.data_url})`)
  }
  return String(marked.parse(md))
})

const onFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) emit('uploadPdf', file)
  input.value = ''
}

const clearAll = () => {
  props.form.requirementText = ''
  feishuUrl.value = ''
  showFeishuInput.value = false
  emit('clearImportedSource')
}

const canSubmit = () => props.form.requirementText.trim().length > 0 && !props.loading

// 滚动同步
const editorRef = ref<HTMLTextAreaElement | null>(null)
const previewRef = ref<HTMLElement | null>(null)
let syncing = false

const syncScroll = (source: 'editor' | 'preview') => {
  if (syncing) return
  syncing = true
  const from = source === 'editor' ? editorRef.value : previewRef.value
  const to = source === 'editor' ? previewRef.value : editorRef.value
  if (from && to) {
    const ratio = from.scrollTop / (from.scrollHeight - from.clientHeight || 1)
    to.scrollTop = ratio * (to.scrollHeight - to.clientHeight || 1)
  }
  requestAnimationFrame(() => { syncing = false })
}

const importFeishuDoc = async () => {
  const url = feishuUrl.value.trim()
  if (!url) return
  feishuLoading.value = true
  feishuError.value = ''
  try {
    const result = await api.feishuFetchDoc(url)
    props.form.requirementText = result.markdown
    emit('importFeishu', {
      title: result.title,
      markdown: result.markdown,
      images: result.images,
      url,
      sourceType: result.source_type,
    })
    showFeishuInput.value = false
  } catch (e) {
    feishuError.value = e instanceof Error ? e.message : '获取文档失败'
  } finally {
    feishuLoading.value = false
  }
}
</script>

<template>
  <div class="ri-layout">

    <!-- Header -->
    <div class="ri-header">
      <div class="ri-eyebrow">Step 1 · 需求输入</div>
      <h2 class="ri-title">描述你要测试的需求</h2>
    </div>

    <!-- 平台 & 项目选择 -->
    <div class="ri-config-row">
      <span class="ri-config-label">平台</span>
      <div class="ri-seg-ctrl">
        <button
          v-for="p in platforms"
          :key="p.value"
          class="ri-seg-btn"
          :class="{ active: form.platform === p.value }"
          :title="p.description"
          @click="form.platform = p.value"
        >{{ p.label }}</button>
      </div>
      <span class="ri-config-label" style="margin-left: 16px;">项目</span>
      <select class="ri-project-select" v-model="form.project">
        <option value="">未指定</option>
        <option v-for="project in projects" :key="project.value" :value="project.value">{{ project.label }}</option>
      </select>
    </div>

    <!-- 导入方式工具栏 -->
    <div class="ri-import-bar">
      <label class="ri-import-btn" :class="{ disabled: uploadingPdf }">
        <input type="file" accept=".pdf" @change="onFileChange" :disabled="uploadingPdf" />
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        {{ uploadingPdf ? '解析中…' : '上传 PDF' }}
      </label>
      <button class="ri-import-btn" @click="showFeishuInput = !showFeishuInput" :disabled="feishuLoading">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
        </svg>
        {{ feishuLoading ? '获取中…' : '导入飞书文档' }}
      </button>
      <div v-if="sourceTitle || pdfFileName" class="ri-source-badge">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        {{ sourceTitle || pdfFileName }}
        <button @click="clearAll" title="清除">&times;</button>
      </div>
    </div>

    <!-- 飞书链接输入 -->
    <div v-if="showFeishuInput" class="ri-feishu-row">
      <input v-model="feishuUrl" class="ri-feishu-url" placeholder="粘贴飞书文档链接，如 https://xxx.feishu.cn/docx/ABC123" @keydown.enter="importFeishuDoc" :disabled="feishuLoading" />
      <button class="btn btn-primary btn-sm" :disabled="feishuLoading || !feishuUrl.trim()" @click="importFeishuDoc">{{ feishuLoading ? '获取中…' : '获取' }}</button>
      <button class="btn btn-ghost btn-sm" @click="showFeishuInput = false">取消</button>
    </div>
    <div v-if="feishuError" class="ri-feishu-error">{{ feishuError }}</div>

    <!-- ═══ 核心区域：左右分栏（编辑 + 预览） ═══ -->
    <div class="ri-split" :class="{ 'ri-split--full': hasContent }">
      <!-- 左：编辑器 -->
      <div class="ri-split-editor">
        <div class="ri-split-label">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          编辑
          <span class="ri-split-count">{{ form.requirementText.length }} 字</span>
        </div>
        <textarea
          ref="editorRef"
          class="ri-split-textarea"
          v-model="form.requirementText"
          placeholder="粘贴 PRD 或手动输入需求描述…

支持 Markdown 格式，导入飞书文档后可直接编辑。"
          @scroll="syncScroll('editor')"
        ></textarea>
      </div>

      <!-- 右：实时预览 -->
      <div class="ri-split-preview">
        <div class="ri-split-label">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
          </svg>
          预览
          <span v-if="sourceImages.length" class="ri-split-img-count">{{ sourceImages.length }} 张图片</span>
        </div>
        <div ref="previewRef" class="ri-split-preview-body" v-html="renderedPreviewHtml" @scroll="syncScroll('preview')"></div>
      </div>
    </div>

    <!-- 提交 -->
    <div class="ri-submit-row">
      <button class="btn btn-primary ri-submit-btn" :disabled="!canSubmit()" @click="emit('submit')">
        <svg v-if="!loading" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        <svg v-else class="ri-spin" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
        {{ loading ? 'AI 解析中…' : '开始 AI 解析' }}
      </button>
    </div>

  </div>
</template>

<style scoped>
/* 导入工具栏 */
.ri-import-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.ri-import-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text-sub);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.ri-import-btn input[type="file"] { display: none; }
.ri-import-btn:hover { border-color: var(--primary-border); color: var(--primary); }
.ri-import-btn.disabled, .ri-import-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.ri-source-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 6px;
  font-size: 12px;
  margin-left: auto;
}
.ri-source-badge button {
  background: none; border: none; color: var(--primary); cursor: pointer;
  font-size: 14px; line-height: 1; padding: 0 2px; opacity: 0.6;
}
.ri-source-badge button:hover { opacity: 1; }

/* 飞书链接行 */
.ri-feishu-row { display: flex; gap: 8px; margin-bottom: 10px; }
.ri-feishu-url {
  flex: 1; padding: 7px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  font-size: 13px; background: var(--surface);
}
.ri-feishu-url:focus { border-color: var(--border-focus); outline: none; }
.ri-feishu-error { color: var(--danger); font-size: 12px; margin-bottom: 8px; }

/* ═══ 左右分栏 ═══ */
.ri-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
  min-height: 400px;
}
.ri-split-editor, .ri-split-preview {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--surface);
}
.ri-split-label {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.ri-split-count { margin-left: auto; font-weight: 400; }
.ri-split-img-count { margin-left: auto; color: var(--primary); font-weight: 400; }

.ri-split-textarea {
  flex: 1;
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  padding: 14px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  line-height: 1.7;
  color: var(--text);
  background: transparent;
  min-height: 350px;
}

.ri-split-preview-body {
  flex: 1;
  padding: 14px 18px;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-sub);
  max-height: 600px;
}
.ri-split-preview-body h1 { font-size: 20px; margin: 14px 0 6px; color: var(--text); font-weight: 700; }
.ri-split-preview-body h2 { font-size: 17px; margin: 12px 0 5px; color: var(--text); font-weight: 700; }
.ri-split-preview-body h3 { font-size: 15px; margin: 10px 0 4px; color: var(--text); font-weight: 600; }
.ri-split-preview-body h4, .ri-split-preview-body h5, .ri-split-preview-body h6 { font-size: 14px; margin: 8px 0 3px; color: var(--text); }
.ri-split-preview-body p { margin: 5px 0; }
.ri-split-preview-body ul, .ri-split-preview-body ol { margin: 5px 0; padding-left: 22px; }
.ri-split-preview-body li { margin: 2px 0; }
.ri-split-preview-body blockquote { margin: 6px 0; padding: 6px 12px; border-left: 3px solid var(--primary-border); background: var(--bg); color: var(--text-muted); font-size: 13px; }
.ri-split-preview-body pre { margin: 6px 0; padding: 10px; background: #1e293b; color: #e2e8f0; border-radius: 6px; overflow-x: auto; font-size: 12px; }
.ri-split-preview-body code { font-size: 12px; background: var(--bg); padding: 1px 4px; border-radius: 3px; }
.ri-split-preview-body pre code { background: none; padding: 0; }
.ri-split-preview-body table { width: 100%; border-collapse: collapse; margin: 6px 0; }
.ri-split-preview-body th, .ri-split-preview-body td { border: 1px solid var(--border); padding: 5px 8px; font-size: 12px; text-align: left; }
.ri-split-preview-body th { background: var(--bg); font-weight: 600; }
.ri-split-preview-body img { max-width: 100%; border-radius: 6px; margin: 6px 0; }
.ri-split-preview-body strong { font-weight: 700; }

@media (max-width: 768px) {
  .ri-split { grid-template-columns: 1fr; }
}
</style>
