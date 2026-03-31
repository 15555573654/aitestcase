<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import MindMapView from '../components/MindMapView.vue'
import { categoryLabels } from '../types'
import type {
  GenerateTestPointsResponse,
  ReviewTestPointsResponse,
  StructuredSummary,
  TestCategory,
  TestPoint,
} from '../types'

const props = defineProps<{
  apiBaseUrl: string
  platform: string
  summary: StructuredSummary
  designResult: GenerateTestPointsResponse
  reviewResult: ReviewTestPointsResponse | null
  selectedIds: string[]
  reviewing: boolean
  generatingCases: boolean
}>()

const emit = defineEmits<{
  togglePoint: [id: string]
  selectAll: []
  clearSelection: []
  review: []
  generateCases: []
  addPoint: [point: TestPoint]
  removePoint: [id: string]
  updatePoint: [point: TestPoint]
}>()

const functions = computed(() => props.designResult.functions)
const flows = computed(() => props.designResult.flows)

const filterModule = ref('all')
const viewMode = ref<'list' | 'mindmap'>('list')
const collapsedKeys = reactive<Record<string, boolean>>({})
const expandedPointId = ref<string | null>(null)
const editingPointId = ref<string | null>(null)
const editForm = reactive<Partial<TestPoint>>({})
const showAddForm = ref(false)
const addForm = reactive({
  title: '',
  function_module: '',
  category: 'positive' as TestPoint['category'],
  description: '',
  risk_level: 'medium' as TestPoint['risk_level'],
  priority: 'P1' as TestPoint['priority'],
})

const displayedPoints = computed(() =>
  props.reviewResult?.reviewed_test_points.length
    ? props.reviewResult.reviewed_test_points
    : props.designResult?.test_points || [],
)

const modules = computed(() => ['all', ...functions.value])

const filteredPoints = computed(() =>
  displayedPoints.value.filter(
    item => filterModule.value === 'all' || item.function_module === filterModule.value,
  ),
)

// 二级分组：模块 → 分类
const groupedByModuleAndCategory = computed(() => {
  const result: Record<string, Record<string, TestPoint[]>> = {}
  for (const point of filteredPoints.value) {
    const mod = point.function_module || '未归类'
    const cat = point.category
    if (!result[mod]) result[mod] = {}
    if (!result[mod][cat]) result[mod][cat] = []
    result[mod][cat].push(point)
  }
  return result
})

const moduleStats = (mod: string) => {
  const cats = groupedByModuleAndCategory.value[mod] || {}
  const all = Object.values(cats).flat()
  return {
    total: all.length,
    selected: all.filter(p => props.selectedIds.includes(p.id)).length,
    highRisk: all.filter(p => p.risk_level === 'high').length,
  }
}

const isModuleAllSelected = (mod: string) => {
  const cats = groupedByModuleAndCategory.value[mod] || {}
  return Object.values(cats).flat().every(p => props.selectedIds.includes(p.id))
}

const toggleModuleSelect = (mod: string) => {
  const cats = groupedByModuleAndCategory.value[mod] || {}
  const all = Object.values(cats).flat()
  if (isModuleAllSelected(mod)) {
    all.forEach(p => { if (props.selectedIds.includes(p.id)) emit('togglePoint', p.id) })
  } else {
    all.forEach(p => { if (!props.selectedIds.includes(p.id)) emit('togglePoint', p.id) })
  }
}

const toggleCollapse = (key: string) => { collapsedKeys[key] = !collapsedKeys[key] }
const toggleExpand = (id: string) => { expandedPointId.value = expandedPointId.value === id ? null : id }

// 编辑
const startEdit = (point: TestPoint) => {
  editingPointId.value = point.id
  Object.assign(editForm, { ...point })
}

const cancelEdit = () => { editingPointId.value = null }

const saveEdit = () => {
  if (!editingPointId.value || !editForm.title || !editForm.description) return
  const updated: TestPoint = {
    id: editingPointId.value,
    title: (editForm.title || '').trim(),
    function_module: editForm.function_module || '',
    category: (editForm.category || 'positive') as TestCategory,
    description: (editForm.description || '').trim(),
    source: editForm.source || '',
    risk_level: (editForm.risk_level || 'medium') as TestPoint['risk_level'],
    priority: (editForm.priority || 'P1') as TestPoint['priority'],
    platform_specific: editForm.platform_specific || false,
  }
  emit('updatePoint', updated)
  editingPointId.value = null
}

// 新增
const nextTpId = computed(() => {
  const maxNum = displayedPoints.value.reduce((max, p) => {
    const match = p.id.match(/^TP-(\d+)$/)
    return match ? Math.max(max, parseInt(match[1])) : max
  }, 0)
  return `TP-${String(maxNum + 1).padStart(3, '0')}`
})

const resetAddForm = () => {
  addForm.title = ''
  addForm.function_module = functions.value[0] || ''
  addForm.category = 'positive'
  addForm.description = ''
  addForm.risk_level = 'medium'
  addForm.priority = 'P1'
}

const openAddForm = () => { resetAddForm(); showAddForm.value = true }

const submitAddForm = () => {
  if (!addForm.title.trim() || !addForm.description.trim()) return
  emit('addPoint', {
    id: nextTpId.value,
    title: addForm.title.trim(),
    function_module: addForm.function_module || '未归类',
    category: addForm.category,
    description: addForm.description.trim(),
    source: '人工添加',
    risk_level: addForm.risk_level,
    priority: addForm.priority,
    platform_specific: false,
  })
  showAddForm.value = false
}
</script>

<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <div class="panel-eyebrow">Step 3 · 测试设计</div>
        <h2>测试点选择与编辑</h2>
      </div>
      <div class="action-group">
        <button class="btn btn-secondary" :disabled="reviewing" @click="emit('review')">
          {{ reviewing ? 'AI 审核中...' : 'AI Diff 审核' }}
        </button>
        <button
          class="btn btn-primary"
          :disabled="generatingCases || selectedIds.length === 0"
          @click="emit('generateCases')"
        >
          {{ generatingCases ? '生成中...' : `生成用例（${selectedIds.length}）` }}
        </button>
      </div>
    </div>

    <!-- 结构信息概览 -->
    <div class="structure-bar">
      <div class="structure-bar-item">
        <span class="structure-bar-label">模块</span>
        <span v-for="fn in functions" :key="fn" class="structure-bar-tag">{{ fn }}</span>
      </div>
      <div v-if="flows.length" class="structure-bar-item">
        <span class="structure-bar-label">业务流</span>
        <span v-for="fl in flows" :key="fl" class="structure-bar-tag structure-bar-tag--flow">{{ fl }}</span>
      </div>
    </div>

    <div class="toolbar">
      <div class="toolbar-group">
        <select v-model="filterModule">
          <option v-for="name in modules" :key="name" :value="name">
            {{ name === 'all' ? '全部模块' : name }}
          </option>
        </select>
        <button class="btn btn-ghost" @click="emit('selectAll')">全选</button>
        <button class="btn btn-ghost" @click="emit('clearSelection')">清空</button>
        <button class="btn btn-ghost" @click="openAddForm">+ 添加</button>
      </div>
      <div class="toolbar-group">
        <span class="toolbar-stat">{{ selectedIds.length }}/{{ displayedPoints.length }} 选中</span>
        <button class="btn btn-ghost" :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">列表</button>
        <button class="btn btn-ghost" :class="{ active: viewMode === 'mindmap' }" @click="viewMode = 'mindmap'">脑图</button>
      </div>
    </div>

    <!-- 添加表单 -->
    <div v-if="showAddForm" class="add-point-form">
      <div class="add-point-form-header">
        <strong>添加测试点</strong>
        <button class="btn btn-ghost" @click="showAddForm = false">&times;</button>
      </div>
      <div class="form-grid">
        <label class="field"><span>标题</span><input v-model="addForm.title" placeholder="测试点标题" /></label>
        <label class="field"><span>模块</span>
          <select v-model="addForm.function_module"><option v-for="fn in functions" :key="fn" :value="fn">{{ fn }}</option></select>
        </label>
      </div>
      <label class="field"><span>描述</span><textarea v-model="addForm.description" rows="2" placeholder="测试目的和预期"></textarea></label>
      <div class="form-grid form-grid-advanced">
        <label class="field"><span>分类</span><select v-model="addForm.category"><option v-for="(label, key) in categoryLabels" :key="key" :value="key">{{ label }}</option></select></label>
        <label class="field"><span>风险</span><select v-model="addForm.risk_level"><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
        <label class="field"><span>优先级</span><select v-model="addForm.priority"><option value="P0">P0</option><option value="P1">P1</option><option value="P2">P2</option></select></label>
      </div>
      <div class="action-group" style="justify-content: flex-end; margin-top: 8px">
        <button class="btn btn-secondary" @click="showAddForm = false">取消</button>
        <button class="btn btn-primary" :disabled="!addForm.title.trim() || !addForm.description.trim()" @click="submitAddForm">添加 ({{ nextTpId }})</button>
      </div>
    </div>

    <!-- AI 审核建议 -->
    <div v-if="reviewResult?.review_notes.length" class="review-notes">
      <div class="sub-title">AI 审核建议</div>
      <div v-for="note in reviewResult.review_notes" :key="`${note.note_type}-${note.target_test_point_id}-${note.message}`" class="review-note">
        <span class="pill pill-info">{{ note.note_type }}</span>
        <span>{{ note.message }}</span>
      </div>
    </div>

    <!-- 脑图 -->
    <MindMapView
      v-if="viewMode === 'mindmap'"
      :api-base-url="apiBaseUrl"
      :platform="platform"
      :summary="summary"
      :functions="functions"
      :test-points="displayedPoints"
      :cases="[]"
      :integration-tests="[]"
    />

    <!-- 二级分组列表：模块 → 分类 -->
    <div v-else class="point-list">
      <div v-for="(categories, mod) in groupedByModuleAndCategory" :key="mod" class="point-group">
        <!-- 模块头 -->
        <div class="point-group-header" @click="toggleCollapse(`mod:${mod}`)">
          <div class="point-group-left">
            <span class="point-group-arrow" :class="{ collapsed: collapsedKeys[`mod:${mod}`] }">&#9662;</span>
            <input type="checkbox" :checked="isModuleAllSelected(mod)" @click.stop="toggleModuleSelect(mod)" />
            <strong>{{ mod }}</strong>
          </div>
          <div class="point-group-stats">
            <span>{{ moduleStats(mod).selected }}/{{ moduleStats(mod).total }} 选中</span>
            <span v-if="moduleStats(mod).highRisk" class="pill pill-danger pill-sm">{{ moduleStats(mod).highRisk }} 高风险</span>
          </div>
        </div>

        <div v-show="!collapsedKeys[`mod:${mod}`]" class="point-group-body">
          <!-- 分类子组 -->
          <div v-for="(points, cat) in categories" :key="cat" class="category-group">
            <div class="category-header" @click="toggleCollapse(`${mod}:${cat}`)">
              <span class="category-arrow" :class="{ collapsed: collapsedKeys[`${mod}:${cat}`] }">&#9662;</span>
              <span class="category-label">{{ categoryLabels[cat as keyof typeof categoryLabels] || cat }}</span>
              <span class="category-count">{{ points.length }}</span>
            </div>

            <div v-show="!collapsedKeys[`${mod}:${cat}`]" class="category-body">
              <div v-for="point in points" :key="point.id" class="point-row">
                <!-- 编辑态 -->
                <div v-if="editingPointId === point.id" class="point-edit-form">
                  <div class="form-grid">
                    <label class="field"><span>标题</span><input v-model="editForm.title" /></label>
                    <label class="field"><span>模块</span>
                      <select v-model="editForm.function_module"><option v-for="fn in functions" :key="fn" :value="fn">{{ fn }}</option></select>
                    </label>
                  </div>
                  <label class="field"><span>描述</span><textarea v-model="editForm.description" rows="2"></textarea></label>
                  <div class="form-grid form-grid-advanced">
                    <label class="field"><span>分类</span><select v-model="editForm.category"><option v-for="(label, key) in categoryLabels" :key="key" :value="key">{{ label }}</option></select></label>
                    <label class="field"><span>风险</span><select v-model="editForm.risk_level"><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
                    <label class="field"><span>优先级</span><select v-model="editForm.priority"><option value="P0">P0</option><option value="P1">P1</option><option value="P2">P2</option></select></label>
                  </div>
                  <div class="action-group" style="justify-content: flex-end; margin-top: 6px; gap: 6px">
                    <button class="btn btn-ghost btn-sm" @click="cancelEdit">取消</button>
                    <button class="btn btn-primary btn-sm" @click="saveEdit">保存</button>
                  </div>
                </div>

                <!-- 展示态 -->
                <div v-else class="point-compact" @click="toggleExpand(point.id)">
                  <input
                    :checked="selectedIds.includes(point.id)"
                    type="checkbox"
                    @click.stop
                    @change="emit('togglePoint', point.id)"
                  />
                  <div class="point-compact-body">
                    <div class="point-compact-top">
                      <span class="point-compact-id">{{ point.id }}</span>
                      <span class="point-compact-title">{{ point.title }}</span>
                      <div class="point-badges">
                        <span class="pill" :class="point.risk_level === 'high' ? 'pill-danger' : 'pill-info'">{{ point.risk_level }}</span>
                        <span class="pill">{{ point.priority }}</span>
                      </div>
                    </div>
                    <!-- 展开详情 -->
                    <div v-if="expandedPointId === point.id" class="point-detail">
                      <p>{{ point.description }}</p>
                      <div class="point-detail-meta">
                        <span>来源：{{ point.source }}</span>
                        <span v-if="point.platform_specific" class="pill pill-sm">平台专项</span>
                      </div>
                      <div class="point-detail-actions">
                        <button class="btn btn-ghost btn-sm" @click.stop="startEdit(point)">编辑</button>
                        <button class="btn btn-ghost btn-sm btn-danger" @click.stop="emit('removePoint', point.id)">删除</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.structure-bar { display: flex; flex-wrap: wrap; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border, #e2e8f0); margin-bottom: 12px; }
.structure-bar-item { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.structure-bar-label { font-size: 12px; color: var(--text-faint, #94a3b8); font-weight: 600; }
.structure-bar-tag { font-size: 12px; padding: 2px 8px; background: var(--bg-subtle, #f1f5f9); border-radius: 4px; color: var(--text-secondary, #475569); }
.structure-bar-tag--flow { background: #eff6ff; color: #3b82f6; }

.toolbar-stat { font-size: 12px; color: var(--text-faint, #94a3b8); }

.category-group { margin-left: 20px; margin-bottom: 4px; }
.category-header { display: flex; align-items: center; gap: 6px; padding: 4px 0; cursor: pointer; user-select: none; }
.category-arrow { font-size: 10px; color: var(--text-faint); transition: transform 0.15s; display: inline-block; }
.category-arrow.collapsed { transform: rotate(-90deg); }
.category-label { font-size: 12px; font-weight: 600; color: var(--text-secondary, #64748b); }
.category-count { font-size: 11px; color: var(--text-faint, #94a3b8); background: var(--bg-subtle, #f1f5f9); border-radius: 8px; padding: 0 6px; }
.category-body { margin-left: 16px; }

.point-row { border-bottom: 1px solid var(--border-light, #f1f5f9); }
.point-row:last-child { border-bottom: none; }

.point-compact { display: flex; align-items: flex-start; gap: 8px; padding: 6px 4px; cursor: pointer; border-radius: 4px; }
.point-compact:hover { background: var(--bg-subtle, #f8fafc); }
.point-compact input[type="checkbox"] { margin-top: 3px; flex-shrink: 0; }
.point-compact-body { flex: 1; min-width: 0; }
.point-compact-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.point-compact-id { font-size: 11px; color: var(--text-faint, #94a3b8); font-family: monospace; flex-shrink: 0; }
.point-compact-title { font-size: 13px; font-weight: 500; color: var(--text-primary, #1e293b); }

.point-detail { margin-top: 6px; padding: 8px; background: var(--bg-subtle, #f8fafc); border-radius: 6px; font-size: 13px; }
.point-detail p { margin: 0 0 6px; color: var(--text-secondary, #64748b); line-height: 1.5; }
.point-detail-meta { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--text-faint, #94a3b8); margin-bottom: 6px; }
.point-detail-actions { display: flex; gap: 6px; }
.btn-danger { color: #ef4444 !important; }
.btn-danger:hover { background: #fef2f2 !important; }

.point-edit-form { padding: 8px; background: var(--bg-subtle, #f8fafc); border-radius: 6px; margin: 4px 0; }
.point-edit-form .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.point-edit-form .form-grid-advanced { grid-template-columns: 1fr 1fr 1fr; }
.point-edit-form .field { display: flex; flex-direction: column; gap: 2px; }
.point-edit-form .field span { font-size: 11px; color: var(--text-faint); }
.point-edit-form input, .point-edit-form textarea, .point-edit-form select { font-size: 12px; padding: 4px 6px; border: 1px solid var(--border, #e2e8f0); border-radius: 4px; }
</style>
