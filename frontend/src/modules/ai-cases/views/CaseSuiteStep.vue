<script setup lang="ts">
import { computed, ref } from 'vue'
import MindMapView from '../components/MindMapView.vue'
import type {
  GenerateCasesResponse,
  GenerateTestPointsResponse,
  IntegrationTestsResponse,
  ReviewTestPointsResponse,
  StructuredSummary,
  TestPoint,
  ValidationIssue,
} from '../types'

const props = defineProps<{
  apiBaseUrl: string
  platform: string
  summary: StructuredSummary
  designResult: GenerateTestPointsResponse
  reviewResult: ReviewTestPointsResponse | null
  caseSuite: GenerateCasesResponse
  integrationResult: IntegrationTestsResponse | null
  selectedPoints: TestPoint[]
}>()

const emit = defineEmits<{
  generateIntegration: []
}>()

const mode = ref<'list' | 'mindmap'>('list')

// 知识库
import { createWorkflowApi } from '../api'
const kbApi = createWorkflowApi(props.apiBaseUrl)
const showKnowledgePanel = ref(false)
const knowledgeDraft = ref('')
const knowledgeExisting = ref('')
const knowledgeLoading = ref(false)
const knowledgeSaving = ref(false)

const generateKnowledgeDraft = async () => {
  knowledgeLoading.value = true
  showKnowledgePanel.value = true
  try {
    const result = await kbApi.generateKnowledgeDraft({
      project: props.platform,
      requirement_text: '',
      summary_title: props.summary.title,
      business_rules: props.summary.business_rules,
      test_points_summary: props.selectedPoints.map(p => `${p.title} (${p.category})`).join('\n'),
    })
    knowledgeDraft.value = result.draft
    knowledgeExisting.value = result.existing
  } catch { knowledgeDraft.value = '生成失败，请手动编写' }
  finally { knowledgeLoading.value = false }
}

const saveKnowledge = async () => {
  knowledgeSaving.value = true
  try {
    const content = knowledgeExisting.value
      ? knowledgeExisting.value + '\n\n' + knowledgeDraft.value
      : knowledgeDraft.value
    await kbApi.saveKnowledge(props.platform, content)
    showKnowledgePanel.value = false
  } catch { /* ignore */ }
  finally { knowledgeSaving.value = false }
}
const filter = ref<'all' | 'cases' | 'integration'>('all')

const points = computed(() =>
  props.reviewResult?.reviewed_test_points.length
    ? props.reviewResult.reviewed_test_points
    : props.designResult.test_points,
)

const integrationTests = computed(() => props.integrationResult?.integration_tests || [])

const issuesByCase = computed(() => {
  const map: Record<string, ValidationIssue[]> = {}
  for (const issue of props.caseSuite.validation_issues) {
    if (issue.target_id) {
      if (!map[issue.target_id]) map[issue.target_id] = []
      map[issue.target_id].push(issue)
    }
  }
  return map
})

const exportCsv = () => {
  const BOM = '\uFEFF'
  const headers = ['用例ID', '标题', '功能模块', '优先级', '类型', '前置条件', '测试数据', '步骤', '预期结果', '来源测试点']
  const rows = props.caseSuite.cases.map(c => [
    c.id,
    c.title,
    c.function_module,
    c.priority,
    c.case_type,
    c.preconditions.join('\n'),
    c.test_data.join('\n'),
    c.steps.map((s, i) => `${i + 1}. ${s}`).join('\n'),
    c.expected_results.map((r, i) => `${i + 1}. ${r}`).join('\n'),
    c.source_test_point_id,
  ])

  const escape = (val: string) => {
    if (val.includes(',') || val.includes('"') || val.includes('\n'))
      return `"${val.replace(/"/g, '""')}"`
    return val
  }

  const csvContent = BOM + [headers, ...rows].map(row => row.map(escape).join(',')).join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `test-cases-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

const exportIntegrationCsv = () => {
  const BOM = '\uFEFF'
  const headers = ['ID', '标题', '描述', '关联流程', '前置条件', '步骤', '预期结果']
  const rows = integrationTests.value.map(t => [
    t.id,
    t.title,
    t.description,
    t.flow,
    t.preconditions.join('\n'),
    t.steps.map((s, i) => `${i + 1}. ${s}`).join('\n'),
    t.expected_results.map((r, i) => `${i + 1}. ${r}`).join('\n'),
  ])

  const escape = (val: string) => {
    if (val.includes(',') || val.includes('"') || val.includes('\n'))
      return `"${val.replace(/"/g, '""')}"`
    return val
  }

  const csvContent = BOM + [headers, ...rows].map(row => row.map(escape).join(',')).join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `integration-tests-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <div class="panel-eyebrow">Step 4</div>
        <h2>用例与回归资产</h2>
      </div>
      <div class="action-group">
        <button class="btn btn-ghost" :class="{ active: mode === 'list' }" @click="mode = 'list'">列表</button>
        <button class="btn btn-ghost" :class="{ active: mode === 'mindmap' }" @click="mode = 'mindmap'">脑图</button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-label">功能用例</span>
        <strong>{{ caseSuite.cases.length }}</strong>
      </div>
      <div class="stat-card">
        <span class="stat-label">联动测试</span>
        <strong>{{ integrationTests.length }}</strong>
      </div>
      <div class="stat-card">
        <span class="stat-label">质量问题</span>
        <strong>{{ caseSuite.validation_issues.length }}</strong>
      </div>
    </div>

    <MindMapView
      v-if="mode === 'mindmap'"
      :api-base-url="apiBaseUrl"
      :platform="platform"
      :summary="summary"
      :functions="designResult.functions"
      :test-points="points"
      :cases="caseSuite.cases"
      :integration-tests="integrationTests"
    />

    <template v-else>
      <div class="toolbar">
        <div class="toolbar-group">
          <button class="btn btn-ghost" :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
          <button class="btn btn-ghost" :class="{ active: filter === 'cases' }" @click="filter = 'cases'">功能用例</button>
          <button class="btn btn-ghost" :class="{ active: filter === 'integration' }" @click="filter = 'integration'">联动测试</button>
        </div>
        <div class="toolbar-group">
          <button
            v-if="filter === 'all' || filter === 'cases'"
            class="btn btn-secondary btn-sm"
            @click="exportCsv"
          >
            导出功能用例 CSV
          </button>
          <button
            v-if="(filter === 'all' || filter === 'integration') && integrationTests.length"
            class="btn btn-secondary btn-sm"
            @click="exportIntegrationCsv"
          >
            导出联动测试 CSV
          </button>
        </div>
      </div>

      <div v-if="caseSuite.validation_issues.length && (filter === 'all')" class="issue-section">
        <div class="sub-title">质量校验</div>
        <div
          v-for="issue in caseSuite.validation_issues.filter(i => !i.target_id)"
          :key="`${issue.issue_type}-${issue.message}`"
          class="issue-item"
        >
          <span class="pill" :class="issue.severity === 'high' ? 'pill-danger' : 'pill-info'">{{ issue.severity }}</span>
          <span>{{ issue.message }}</span>
        </div>
      </div>

      <div v-if="filter === 'all' || filter === 'cases'" class="suite-section">
        <div class="sub-title">功能用例</div>
        <div v-for="item in caseSuite.cases" :key="item.id" class="case-card">
          <div class="suite-top">
            <strong>{{ item.id }} {{ item.title }}</strong>
            <div class="point-badges">
              <span class="pill">{{ item.function_module }}</span>
              <span class="pill">{{ item.priority }}</span>
              <span class="pill">{{ item.case_type }}</span>
            </div>
          </div>
          <div v-if="issuesByCase[item.id]?.length" class="case-inline-issues">
            <span
              v-for="issue in issuesByCase[item.id]"
              :key="issue.message"
              class="case-issue-tag"
              :class="issue.severity === 'high' ? 'issue-high' : 'issue-medium'"
              :title="issue.message"
            >
              {{ issue.issue_type }}：{{ issue.message }}
            </span>
          </div>
          <div class="case-grid">
            <div>
              <div class="mini-title">前置条件</div>
              <ul><li v-for="value in item.preconditions" :key="value">{{ value }}</li></ul>
            </div>
            <div>
              <div class="mini-title">测试数据</div>
              <ul><li v-for="value in item.test_data" :key="value">{{ value }}</li></ul>
            </div>
            <div>
              <div class="mini-title">步骤</div>
              <ol><li v-for="value in item.steps" :key="value">{{ value }}</li></ol>
            </div>
            <div>
              <div class="mini-title">预期结果</div>
              <ol><li v-for="value in item.expected_results" :key="value">{{ value }}</li></ol>
            </div>
          </div>
        </div>
      </div>

      <div v-if="filter === 'all' || filter === 'integration'" class="suite-section">
        <div class="sub-title" style="display:flex;align-items:center;gap:8px">
          联动测试
          <button
            v-if="integrationTests.length === 0"
            class="btn btn-secondary btn-sm"
            @click="emit('generateIntegration')"
          >
            生成联动测试
          </button>
        </div>
        <div v-if="integrationTests.length === 0" class="empty-state">点击上方按钮生成跨模块联动测试场景。</div>
        <div v-for="item in integrationTests" :key="item.id" class="case-card">
          <div class="suite-top">
            <strong>{{ item.id }} {{ item.title }}</strong>
            <span class="pill">{{ item.flow }}</span>
          </div>
          <p>{{ item.description }}</p>
          <div class="case-grid">
            <div>
              <div class="mini-title">前置条件</div>
              <ul><li v-for="value in item.preconditions" :key="value">{{ value }}</li></ul>
            </div>
            <div>
              <div class="mini-title">步骤</div>
              <ol><li v-for="value in item.steps" :key="value">{{ value }}</li></ol>
            </div>
            <div>
              <div class="mini-title">预期结果</div>
              <ol><li v-for="value in item.expected_results" :key="value">{{ value }}</li></ol>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 知识库沉淀 -->
    <div class="kb-section">
      <button class="btn btn-ghost" @click="generateKnowledgeDraft" :disabled="knowledgeLoading">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
        </svg>
        {{ knowledgeLoading ? 'AI 总结中…' : '沉淀到知识库' }}
      </button>
    </div>

    <!-- 知识库编辑面板 -->
    <div v-if="showKnowledgePanel" class="kb-panel">
      <div class="kb-panel-header">
        <strong>知识库草稿（请审核后保存）</strong>
        <button class="btn btn-ghost btn-sm" @click="showKnowledgePanel = false">&times;</button>
      </div>
      <div v-if="knowledgeExisting" class="kb-existing">
        <div class="kb-existing-label">已有知识库内容：</div>
        <pre>{{ knowledgeExisting }}</pre>
      </div>
      <div class="kb-draft-label">AI 生成的补充内容（可编辑）：</div>
      <textarea class="kb-draft-textarea" v-model="knowledgeDraft" rows="12"></textarea>
      <div class="kb-panel-actions">
        <button class="btn btn-ghost" @click="showKnowledgePanel = false">取消</button>
        <button class="btn btn-primary" :disabled="knowledgeSaving || !knowledgeDraft.trim()" @click="saveKnowledge">
          {{ knowledgeSaving ? '保存中…' : '确认保存到知识库' }}
        </button>
      </div>
    </div>
  </section>
</template>
