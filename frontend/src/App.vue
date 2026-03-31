<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import CaseSuiteStep from './modules/ai-cases/views/CaseSuiteStep.vue'
import HistorySidebar from './modules/ai-cases/components/HistorySidebar.vue'
import RequirementInputStep from './modules/ai-cases/views/RequirementInputStep.vue'
import SummaryConfirmStep from './modules/ai-cases/views/SummaryConfirmStep.vue'
import TestDesignStep from './modules/ai-cases/views/TestDesignStep.vue'
import DataSearch from './modules/bq-query/views/DataSearch.vue'
import AgentChat from './modules/bq-query/views/AgentChat.vue'
import { createWorkflowApi } from './modules/ai-cases/api'
import { createBqApi } from './modules/bq-query/api'
import type {
  ClarificationAnswer,
  ClarifyResponse,
  GenerateCasesResponse,
  GenerateTestPointsResponse,
  HistoryRecord,
  HistoryStage,
  IntegrationTestsResponse,
  ReviewTestPointsResponse,
  StructuredSummary,
  TaskFormState,
  TestPoint,
} from './modules/ai-cases/types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
const api = createWorkflowApi(apiBaseUrl)
const bqApi = createBqApi(apiBaseUrl)

const meta = {
  platforms: [
    { label: 'Web', value: 'web' as const, description: '后台、官网、表单' },
    { label: 'App', value: 'app' as const, description: 'iOS / Android 客户端' },
    { label: '插件', value: 'plugin' as const, description: '浏览器插件、IDE 扩展等' },
  ],
  projects: [{ label: 'Solvely', value: 'solvely' }],
}

const clarifying = ref(false)
const refiningSummary = ref(false)
const generatingDesign = ref(false)
const reviewing = ref(false)
const generatingCases = ref(false)
const uploadingPdf = ref(false)
const pdfFileName = ref('')
const errorMessage = ref('')
const sourceType = ref('')
const sourceTitle = ref('')
const sourceUrl = ref('')
const sourceMarkdown = ref('')
const sourceImages = ref<{ index: number; data_url: string; context: string }[]>([])
const currentStep = ref(1)
const historyRecords = ref<HistoryRecord[]>([])
const activeHistoryId = ref<string | null>(null)
const taskActive = ref(false)
const activeModule = ref<'home' | 'ai-cases' | 'bq-query'>('home')
const moduleView = ref<'intro' | 'workspace'>('intro')
const bqTab = ref<'search' | 'agent'>('search')
const bqSources = ref<{ key: string; label: string }[]>([])
const bqSourceKey = ref('')

const form = reactive<TaskFormState>({
  platform: 'web',
  project: '',
  requirementText: '',
})

const summaryDraft = ref<StructuredSummary | null>(null)
const clarifyResult = ref<ClarifyResponse | null>(null)
const designResult = ref<GenerateTestPointsResponse | null>(null)
const reviewResult = ref<ReviewTestPointsResponse | null>(null)
const caseSuite = ref<GenerateCasesResponse | null>(null)
const integrationResult = ref<IntegrationTestsResponse | null>(null)
const selectedIds = ref<string[]>([])
const clarificationDraftAnswers = reactive<Record<string, string>>({})

const stepLabels = ['需求输入', '摘要确认', '测试设计', '用例与回归资产']

const maxReachedStep = computed(() => {
  if (caseSuite.value) return 4
  if (designResult.value) return 3
  if (summaryDraft.value) return 2
  return 1
})

const displayedPoints = computed(() =>
  reviewResult.value?.reviewed_test_points.length
    ? reviewResult.value.reviewed_test_points
    : designResult.value?.test_points || [],
)

const selectedPoints = computed(() =>
  displayedPoints.value.filter(point => selectedIds.value.includes(point.id)),
)

const hasUnansweredBlocking = computed(() =>
  (clarifyResult.value?.clarification_questions || [])
    .filter(item => item.blocking)
    .some(item => !(clarificationDraftAnswers[item.id] || '').trim()),
)

const isRequirementComplete = computed(() => clarifyResult.value?.is_complete ?? false)

const serialize = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const createEmptySummary = (): StructuredSummary => ({
  title: '',
  business_goal: '',
  actors: [],
  main_flow: [],
  exception_flows: [],
  business_rules: [],
  experiment_groups: [],
})

const deriveTaskTitle = () =>
  sourceTitle.value
  || pdfFileName.value
  || form.requirementText.split('\n').map(item => item.trim()).find(Boolean)?.slice(0, 40)
  || '未命名任务'

const resetWorkflowState = () => {
  summaryDraft.value = null
  clarifyResult.value = null
  designResult.value = null
  reviewResult.value = null
  caseSuite.value = null
  integrationResult.value = null
  selectedIds.value = []
  Object.keys(clarificationDraftAnswers).forEach(key => delete clarificationDraftAnswers[key])
  errorMessage.value = ''
  currentStep.value = 1
}

const startNewTask = () => {
  taskActive.value = true
  activeModule.value = 'ai-cases'
  moduleView.value = 'workspace'
  activeHistoryId.value = null
  form.requirementText = ''
  pdfFileName.value = ''
  sourceType.value = ''
  sourceTitle.value = ''
  sourceUrl.value = ''
  sourceMarkdown.value = ''
  sourceImages.value = []
  resetWorkflowState()
}

const goHome = () => {
  taskActive.value = false
  activeModule.value = 'home'
  moduleView.value = 'intro'
  errorMessage.value = ''
}

const switchModule = (mod: string) => {
  activeModule.value = mod as 'ai-cases' | 'bq-query'
  moduleView.value = 'intro'
  taskActive.value = false
}

const enterBqWorkspace = async () => {
  activeModule.value = 'bq-query'
  moduleView.value = 'workspace'
  if (!bqSources.value.length) {
    try {
      bqSources.value = await bqApi.getSources()
      if (bqSources.value.length && !bqSourceKey.value) {
        bqSourceKey.value = bqSources.value[0].key
      }
    } catch { /* ignore */ }
  }
}

const enterAiCasesIntro = () => {
  activeModule.value = 'ai-cases'
  moduleView.value = 'intro'
  taskActive.value = false
}

const collectClarificationAnswers = (): ClarificationAnswer[] =>
  (clarifyResult.value?.clarification_questions || [])
    .filter(item => (clarificationDraftAnswers[item.id] || '').trim())
    .map(item => ({
      question_id: item.id,
      question: item.question,
      answer: clarificationDraftAnswers[item.id].trim(),
    }))

const startClarify = async () => {
  clarifying.value = true
  errorMessage.value = ''
  resetWorkflowState()
  try {
    const result = await api.clarify(form, [], sourceImages.value.map(img => img.data_url))
    clarifyResult.value = result
    summaryDraft.value = serialize(result.summary)
    currentStep.value = 2
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '需求解析失败'
  } finally {
    clarifying.value = false
  }
}

const refineSummary = async () => {
  if (!summaryDraft.value) return
  refiningSummary.value = true
  errorMessage.value = ''
  try {
    const result = await api.clarify(
      form,
      collectClarificationAnswers(),
      sourceImages.value.map(img => img.data_url),
      summaryDraft.value || undefined,
    )
    clarifyResult.value = result
    summaryDraft.value = serialize(result.summary)
    // 清空旧的回答，避免新问题的输入框中残留上轮内容
    Object.keys(clarificationDraftAnswers).forEach(key => delete clarificationDraftAnswers[key])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '摘要更新失败'
  } finally {
    refiningSummary.value = false
  }
}

const saveCurrentHistory = async (stage: HistoryStage) => {
  if (!summaryDraft.value || !clarifyResult.value) return
  const recordId = activeHistoryId.value || `hist_${Date.now()}`
  const record: HistoryRecord = {
    id: recordId,
    title: summaryDraft.value.title || deriveTaskTitle(),
    platform: form.platform,
    project: form.project,
    stage,
    cases_count: caseSuite.value?.cases.length || 0,
    integration_count: integrationResult.value?.integration_tests.length || 0,
    timestamp: new Date().toISOString(),
    data: {
      task_input: {
        requirement_text: form.requirementText,
        source_type: sourceType.value,
        source_title: sourceTitle.value,
        source_url: sourceUrl.value,
        source_markdown: sourceMarkdown.value,
      },
      test_design: {
        summary: serialize(summaryDraft.value),
        clarification_questions: clarifyResult.value.clarification_questions,
        clarification_answers: collectClarificationAnswers(),
        missing_fields: clarifyResult.value.missing_fields,
        resolved_fields: clarifyResult.value.resolved_fields,
        remaining_risks: clarifyResult.value.remaining_risks,
        functions: designResult.value?.functions || [],
        flows: designResult.value?.flows || [],
        module_segments: designResult.value?.module_segments || {},
        coverage_dimensions: designResult.value?.coverage_dimensions || [],
        test_points: designResult.value?.test_points || [],
        reviewed_test_points: reviewResult.value?.reviewed_test_points || [],
        review_notes: reviewResult.value?.review_notes || [],
      },
      case_suite: caseSuite.value
        ? {
            cases: caseSuite.value.cases,
            integration_tests: integrationResult.value?.integration_tests || [],
            regression_suites: [],
            validation_issues: caseSuite.value.validation_issues,
          }
        : null,
    },
  }

  try {
    await api.saveHistory(record)
    activeHistoryId.value = recordId
    await loadHistory()
  } catch {
    // ignore history errors to avoid blocking the main workflow
  }
}

const saveInputHistory = async () => {
  if (!form.requirementText.trim()) return
  const recordId = activeHistoryId.value || `hist_${Date.now()}`
  const record: HistoryRecord = {
    id: recordId,
    title: deriveTaskTitle(),
    platform: form.platform,
    project: form.project,
    stage: 'summary',
    cases_count: 0,
    integration_count: 0,
    timestamp: new Date().toISOString(),
    data: {
      task_input: {
        requirement_text: form.requirementText,
        source_type: sourceType.value,
        source_title: sourceTitle.value,
        source_url: sourceUrl.value,
        source_markdown: sourceMarkdown.value,
      },
      test_design: {
        summary: createEmptySummary(),
        clarification_questions: [],
        clarification_answers: [],
        missing_fields: [],
        resolved_fields: [],
        remaining_risks: [],
        functions: [],
        flows: [],
        module_segments: {},
        coverage_dimensions: [],
        test_points: [],
        reviewed_test_points: [],
        review_notes: [],
      },
      case_suite: null,
    },
  }

  try {
    await api.saveHistory(record)
    activeHistoryId.value = recordId
    await loadHistory()
  } catch {
    // ignore history errors to avoid blocking the main workflow
  }
}

const generateDesign = async () => {
  if (!summaryDraft.value || !clarifyResult.value) return
  generatingDesign.value = true
  errorMessage.value = ''
  try {
    // 链式调用：先结构分析，再测试点生成，用户只等一次
    const structure = await api.analyzeStructure(
      form.platform,
      summaryDraft.value,
      collectClarificationAnswers(),
      clarifyResult.value.clarification_questions,
    )
    designResult.value = await api.generateTestPoints(
      form.platform,
      summaryDraft.value,
      structure.functions,
      structure.flows,
      structure.module_segments,
      structure.coverage_dimensions,
      collectClarificationAnswers(),
    )
    reviewResult.value = null
    caseSuite.value = null
    integrationResult.value = null
    selectedIds.value = designResult.value.test_points.map(point => point.id)
    currentStep.value = 3
    await saveCurrentHistory('test_design')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '测试设计生成失败'
  } finally {
    generatingDesign.value = false
  }
}

const reviewDesign = async () => {
  if (!designResult.value || !summaryDraft.value) return
  reviewing.value = true
  errorMessage.value = ''
  try {
    reviewResult.value = await api.reviewTestPoints(
      form.platform,
      summaryDraft.value,
      collectClarificationAnswers(),
      designResult.value.test_points,
    )
    selectedIds.value = reviewResult.value.reviewed_test_points.map(point => point.id)
    await saveCurrentHistory('test_design')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '测试点评审失败'
  } finally {
    reviewing.value = false
  }
}

const togglePoint = (id: string) => {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter(item => item !== id)
    : [...selectedIds.value, id]
}

const selectAllPoints = () => {
  selectedIds.value = displayedPoints.value.map(point => point.id)
}

const clearSelection = () => {
  selectedIds.value = []
}

const replaceDisplayedPoints = (nextPoints: TestPoint[]) => {
  if (reviewResult.value) {
    reviewResult.value = {
      ...reviewResult.value,
      reviewed_test_points: nextPoints,
    }
  } else if (designResult.value) {
    designResult.value = {
      ...designResult.value,
      test_points: nextPoints,
    }
  }
}

const addPoint = (point: TestPoint) => {
  replaceDisplayedPoints([...displayedPoints.value, point])
  selectedIds.value = [...selectedIds.value, point.id]
}

const removePoint = (id: string) => {
  replaceDisplayedPoints(displayedPoints.value.filter(point => point.id !== id))
  selectedIds.value = selectedIds.value.filter(item => item !== id)
}

const updatePoint = (updated: TestPoint) => {
  replaceDisplayedPoints(displayedPoints.value.map(p => p.id === updated.id ? updated : p))
}

const generateCases = async () => {
  if (!designResult.value || !summaryDraft.value || selectedPoints.value.length === 0) return
  generatingCases.value = true
  errorMessage.value = ''
  try {
    caseSuite.value = await api.generateCaseSuite(
      form.platform,
      summaryDraft.value,
      designResult.value.functions,
      designResult.value.flows,
      designResult.value.module_segments,
      selectedPoints.value,
    )
    integrationResult.value = null
    currentStep.value = 4
    await saveCurrentHistory('case_suite')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '测试用例生成失败'
  } finally {
    generatingCases.value = false
  }
}

const generateIntegration = async () => {
  if (!designResult.value || !summaryDraft.value || !caseSuite.value) return
  errorMessage.value = ''
  try {
    integrationResult.value = await api.generateIntegrationTests(
      form.platform,
      summaryDraft.value,
      designResult.value.flows,
      selectedPoints.value,
      caseSuite.value.cases.map(c => c.title),
    )
    await saveCurrentHistory('case_suite')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '联动测试生成失败'
  }
}

const handlePdfUpload = async (file: File) => {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    errorMessage.value = '仅支持 PDF 文件'
    return
  }
  uploadingPdf.value = true
  pdfFileName.value = file.name
  errorMessage.value = ''
  try {
    const data = await api.uploadPdf(file)
    form.requirementText = data.text
    sourceType.value = 'pdf'
    sourceTitle.value = file.name
    sourceUrl.value = ''
    sourceMarkdown.value = ''
    sourceImages.value = []
    await saveInputHistory()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'PDF 解析失败'
    pdfFileName.value = ''
  } finally {
    uploadingPdf.value = false
  }
}

const handleFeishuImport = async (payload: {
  title: string
  markdown: string
  images: { index: number; data_url: string; context: string }[]
  url: string
  sourceType: string
}) => {
  sourceType.value = payload.sourceType
  sourceTitle.value = payload.title
  sourceUrl.value = payload.url
  sourceMarkdown.value = payload.markdown
  sourceImages.value = payload.images
  form.requirementText = payload.markdown
  pdfFileName.value = ''
  await saveInputHistory()
}

const clearImportedSource = () => {
  sourceType.value = ''
  sourceTitle.value = ''
  sourceUrl.value = ''
  sourceMarkdown.value = ''
  sourceImages.value = []
  pdfFileName.value = ''
}

const loadHistory = async () => {
  try {
    historyRecords.value = await api.listHistory()
  } catch {
    historyRecords.value = []
  }
}

const loadHistoryRecord = (record: HistoryRecord) => {
  taskActive.value = true
  activeModule.value = 'ai-cases'
  moduleView.value = 'workspace'
  activeHistoryId.value = record.id
  form.platform = record.platform
  form.project = record.project
  form.requirementText = record.data.task_input.requirement_text
  sourceType.value = record.data.task_input.source_type || ''
  sourceTitle.value = record.data.task_input.source_title || ''
  sourceUrl.value = record.data.task_input.source_url || ''
  sourceMarkdown.value = record.data.task_input.source_markdown || ''
  pdfFileName.value = sourceType.value === 'pdf' ? sourceTitle.value : ''
  summaryDraft.value = serialize(record.data.test_design.summary)
  clarifyResult.value = {
    platform: record.platform,
    summary: serialize(record.data.test_design.summary),
    clarification_questions: record.data.test_design.clarification_questions,
    is_complete: true,
    missing_fields: record.data.test_design.missing_fields,
    resolved_fields: record.data.test_design.resolved_fields,
    remaining_risks: record.data.test_design.remaining_risks,
    round: 1,
    prompts: {},
  }
  // 恢复结构分析结果（从 functions/flows 等字段重建）
  designResult.value = record.data.test_design.test_points.length
    ? {
        platform: record.platform,
        functions: record.data.test_design.functions,
        flows: record.data.test_design.flows,
        module_segments: record.data.test_design.module_segments,
        coverage_dimensions: record.data.test_design.coverage_dimensions,
        test_points: record.data.test_design.test_points,
        prompts: {},
      }
    : null
  reviewResult.value = record.data.test_design.reviewed_test_points.length || record.data.test_design.review_notes.length
    ? {
        platform: record.platform,
        reviewed_test_points: record.data.test_design.reviewed_test_points,
        review_notes: record.data.test_design.review_notes,
        validation_issues: [],
        prompts: {},
      }
    : null
  caseSuite.value = record.data.case_suite
    ? {
        platform: record.platform,
        cases: record.data.case_suite.cases,
        validation_issues: record.data.case_suite.validation_issues,
        prompts: {},
      }
    : null
  integrationResult.value = record.data.case_suite?.integration_tests?.length
    ? {
        platform: record.platform,
        integration_tests: record.data.case_suite.integration_tests,
        validation_issues: [],
        prompts: {},
      }
    : null
  selectedIds.value = (reviewResult.value?.reviewed_test_points || designResult.value?.test_points || []).map(point => point.id)
  const hasSummaryContent = Boolean(
    summaryDraft.value?.title
    || summaryDraft.value?.business_goal
    || summaryDraft.value?.main_flow.length
    || clarifyResult.value?.clarification_questions.length,
  )
  if (caseSuite.value) {
    currentStep.value = 4
  } else if (designResult.value) {
    currentStep.value = 3
  } else if (hasSummaryContent) {
    currentStep.value = 2
  } else {
    currentStep.value = 1
  }
  Object.keys(clarificationDraftAnswers).forEach(key => delete clarificationDraftAnswers[key])
  for (const item of record.data.test_design.clarification_answers) {
    clarificationDraftAnswers[item.question_id] = item.answer
  }
  errorMessage.value = ''
}

const deleteHistoryRecord = async (id: string) => {
  try {
    await api.deleteHistory(id)
    if (activeHistoryId.value === id) {
      activeHistoryId.value = null
      goHome()
    }
    await loadHistory()
  } catch {
    // ignore delete failure
  }
}

onMounted(async () => {
  await loadHistory()
})
</script>

<template>
  <div class="app-wrapper">
    <HistorySidebar
      :records="historyRecords"
      :active-id="activeHistoryId"
      :task-active="taskActive"
      :active-module="activeModule"
      @go-home="goHome"
      @new-task="startNewTask"
      @select-record="loadHistoryRecord"
      @delete-record="deleteHistoryRecord"
      @switch-module="switchModule"
      @enter-ai-intro="enterAiCasesIntro"
    />

    <main class="app-main">
      <div v-if="activeModule === 'home' && !taskActive" class="welcome-page">
        <div class="welcome-content">

          <!-- Hero -->
          <div class="welcome-hero">
            <div class="welcome-hero-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
              AI Test Platform · Beta
            </div>
            <h1 class="welcome-title">AI Test</h1>
            <p class="welcome-desc">
              面向测试工程师的 AI 原生工具平台<br>
              测试设计、数据校验、自动化执行
            </p>
          </div>

          <!-- Module Cards -->
          <div class="welcome-section">
            <div class="welcome-section-label">功能模块</div>
            <div class="welcome-module-grid">

              <div class="module-card module-card--active" @click="startNewTask">
                <div class="module-card-header">
                  <div class="module-card-icon" style="background: #EEF2FF;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                  </div>
                  <span class="module-status module-status--live">可用</span>
                </div>
                <div class="module-card-title">AI 生成测试用例</div>
                <div class="module-card-desc">需求澄清 → 测试点设计 → 用例生成全流程</div>
                <div class="module-card-action">
                  开始使用
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                </div>
              </div>

              <div class="module-card module-card--active" @click="switchModule('bq-query')">
                <div class="module-card-header">
                  <div class="module-card-icon" style="background: #FFF7ED;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <ellipse cx="12" cy="5" rx="9" ry="3"/>
                      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                    </svg>
                  </div>
                  <span class="module-status module-status--live">可用</span>
                </div>
                <div class="module-card-title">BQ 数据查询</div>
                <div class="module-card-desc">资源类型筛选 · 用户查询 · AI 智能查询</div>
                <div class="module-card-action">
                  开始使用
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                </div>
              </div>

              <div class="module-card module-card--soon">
                <div class="module-card-header">
                  <div class="module-card-icon" style="background: #F0FDF4;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>
                    </svg>
                  </div>
                  <span class="module-status module-status--soon">规划中</span>
                </div>
                <div class="module-card-title">Android 测试工具</div>
                <div class="module-card-desc">设备管理 · 埋点验证 · 性能监控</div>
              </div>

            </div>
          </div>

        </div>
      </div>
      <!-- AI 测试用例 intro -->
      <div v-else-if="activeModule === 'ai-cases' && moduleView === 'intro'" class="module-intro-page">
        <div class="module-intro-content">
          <div class="module-intro-icon" style="background: #EEF2FF;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <h1 class="module-intro-title">AI 生成测试用例</h1>
          <p class="module-intro-desc">从需求文本一键生成结构化测试用例，覆盖需求澄清、测试点设计、用例生成全流程。</p>

          <div class="module-intro-steps">
            <div class="module-intro-step" v-for="(step, idx) in [
              { num: '1', title: '需求输入', desc: '粘贴需求文本或上传 PDF，补充角色与业务规则' },
              { num: '2', title: '摘要确认', desc: 'AI 提取结构化摘要，识别澄清问题，人工确认' },
              { num: '3', title: '测试设计', desc: '按模块生成测试点，支持 AI 评审、手动编辑' },
              { num: '4', title: '用例生成', desc: '生成功能用例与联动测试，导出测试资产' },
            ]" :key="idx">
              <div class="module-intro-step-num">{{ step.num }}</div>
              <div>
                <div class="module-intro-step-title">{{ step.title }}</div>
                <div class="module-intro-step-desc">{{ step.desc }}</div>
              </div>
            </div>
          </div>

          <button class="btn btn-primary module-intro-cta" @click="startNewTask">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新建测试任务
          </button>
        </div>
      </div>

      <!-- BQ 数据查询 intro -->
      <div v-else-if="activeModule === 'bq-query' && moduleView === 'intro'" class="module-intro-page">
        <div class="module-intro-content">
          <div class="module-intro-icon" style="background: #FFF7ED;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
          </div>
          <h1 class="module-intro-title">BQ 数据查询</h1>
          <p class="module-intro-desc">查询 BigQuery 中的用户资源数据，支持按资源类型筛选、UID 查询和 AI 自然语言查询。</p>

          <div class="module-intro-features">
            <div class="module-intro-feature">
              <div class="module-intro-feature-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </div>
              <div>
                <div class="module-intro-feature-title">资源类型筛选</div>
                <div class="module-intro-feature-desc">按 PDF / PPT / WORD / TXT 等资源类型快速过滤 Flashcards 资源</div>
              </div>
            </div>
            <div class="module-intro-feature">
              <div class="module-intro-feature-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <div>
                <div class="module-intro-feature-title">用户 ID 查询</div>
                <div class="module-intro-feature-desc">通过 uid 精确查看指定用户上传的所有资源及状态</div>
              </div>
            </div>
            <div class="module-intro-feature">
              <div class="module-intro-feature-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>
              </div>
              <div>
                <div class="module-intro-feature-title">AI 智能查询</div>
                <div class="module-intro-feature-desc">用自然语言描述查询需求，Gemini Agent 自动生成 SQL 返回结果</div>
              </div>
            </div>
          </div>

          <button class="btn btn-primary module-intro-cta" @click="enterBqWorkspace">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            开始查询
          </button>
        </div>
      </div>

      <!-- BQ 数据查询工作区 -->
      <div v-else-if="activeModule === 'bq-query' && moduleView === 'workspace'" class="bq-module-layout">
        <div class="bq-module-toolbar">
          <div class="bq-source-tabs">
            <button
              v-for="src in bqSources"
              :key="src.key"
              class="bq-source-tab"
              :class="{ active: bqSourceKey === src.key }"
              @click="bqSourceKey = src.key"
            >{{ src.label }}</button>
          </div>
          <div class="bq-module-tabs">
            <button class="btn btn-ghost" :class="{ active: bqTab === 'search' }" @click="bqTab = 'search'">数据查询</button>
            <button class="btn btn-ghost" :class="{ active: bqTab === 'agent' }" @click="bqTab = 'agent'">AI 智能查询</button>
          </div>
        </div>
        <DataSearch v-if="bqTab === 'search'" :api-base-url="apiBaseUrl" :source-key="bqSourceKey" />
        <AgentChat v-else :api-base-url="apiBaseUrl" :source-key="bqSourceKey" />
      </div>

      <!-- AI 测试用例工作流 -->
      <div v-else class="workbench-layout">
        <div class="step-progress">
          <div
            v-for="(label, idx) in stepLabels"
            :key="label"
            class="step-progress-item"
            :class="{ active: currentStep === idx + 1, completed: maxReachedStep > idx + 1 }"
            @click="idx + 1 <= maxReachedStep ? (currentStep = idx + 1) : null"
          >
            <div class="step-circle">
              <svg v-if="maxReachedStep > idx + 1" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
              </svg>
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <span class="step-label">{{ label }}</span>
            <div v-if="idx < stepLabels.length - 1" class="step-connector" :class="{ filled: maxReachedStep > idx + 1 }"></div>
          </div>
        </div>

        <div v-if="errorMessage" class="error-banner">
          <strong>操作失败：</strong> {{ errorMessage }}
        </div>

        <RequirementInputStep
          v-if="currentStep === 1"
          :form="form"
          :platforms="meta.platforms"
          :projects="meta.projects"
          :loading="clarifying"
          :uploading-pdf="uploadingPdf"
          :pdf-file-name="pdfFileName"
          :api-base-url="apiBaseUrl"
          :source-title="sourceTitle"
          :source-images="sourceImages"
          :source-type="sourceType"
          @submit="startClarify"
          @upload-pdf="handlePdfUpload"
          @import-feishu="handleFeishuImport"
          @clear-imported-source="clearImportedSource"
        />

        <SummaryConfirmStep
          v-else-if="currentStep === 2 && summaryDraft && clarifyResult"
          :summary="summaryDraft"
          :clarification-questions="clarifyResult.clarification_questions"
          :clarification-draft-answers="clarificationDraftAnswers"
          :missing-fields="clarifyResult.missing_fields"
          :remaining-risks="clarifyResult.remaining_risks"
          :is-complete="isRequirementComplete"
          :has-unanswered-blocking="hasUnansweredBlocking"
          :loading-refine="refiningSummary"
          :loading-generate="generatingDesign"
          @refine="refineSummary"
          @generate-design="generateDesign"
        />

        <TestDesignStep
          v-else-if="currentStep === 3 && summaryDraft && designResult"
          :api-base-url="apiBaseUrl"
          :platform="form.platform"
          :summary="summaryDraft"
          :design-result="designResult"
          :review-result="reviewResult"
          :selected-ids="selectedIds"
          :reviewing="reviewing"
          :generating-cases="generatingCases"
          @toggle-point="togglePoint"
          @select-all="selectAllPoints"
          @clear-selection="clearSelection"
          @review="reviewDesign"
          @generate-cases="generateCases"
          @add-point="addPoint"
          @remove-point="removePoint"
          @update-point="updatePoint"
        />

        <CaseSuiteStep
          v-else-if="currentStep === 4 && summaryDraft && designResult && caseSuite"
          :api-base-url="apiBaseUrl"
          :platform="form.platform"
          :summary="summaryDraft"
          :design-result="designResult"
          :review-result="reviewResult"
          :case-suite="caseSuite"
          :integration-result="integrationResult"
          :selected-points="selectedPoints"
          @generate-integration="generateIntegration"
        />
      </div>
    </main>
  </div>
</template>
