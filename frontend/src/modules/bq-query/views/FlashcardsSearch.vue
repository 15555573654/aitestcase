<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createBqApi } from '../api'
import type { FlashcardResource, FlashcardResourceTypeCount } from '../types'

const props = defineProps<{ apiBaseUrl: string }>()
const api = createBqApi(props.apiBaseUrl)

const resourceTypes = ref<FlashcardResourceTypeCount[]>([])
const typesLoading = ref(false)
const loading = ref(false)
const error = ref('')
const results = ref<FlashcardResource[]>([])
const selectedItem = ref<FlashcardResource | null>(null)
const currentOffset = ref(0)
const PAGE_SIZE = 50

const filterForm = reactive({
  resource_type: '',
  uid: '',
  platform: '',
  status: '',
  start_date: '',
  end_date: '',
  include_deleted: false,
})

const PLATFORM_OPTIONS = ['web', 'iOS', 'android', 'unknown']
const TYPE_COLORS: Record<string, string> = {
  PDF: '#EF4444',
  PPT: '#F97316',
  PPTX: '#F97316',
  WORD: '#3B82F6',
  DOC: '#3B82F6',
  DOCX: '#3B82F6',
  TXT: '#6B7280',
  IMAGE: '#10B981',
  VIDEO: '#8B5CF6',
  AUDIO: '#EC4899',
}

const typeColor = (t: string) => TYPE_COLORS[t?.toUpperCase()] ?? '#9CA3AF'
const typeTextColor = (t: string) => TYPE_COLORS[t?.toUpperCase()] ?? '#6B7280'
const typeBg = (t: string) => (TYPE_COLORS[t?.toUpperCase()] ?? '#9CA3AF') + '18'

const hasFilters = computed(() =>
  filterForm.resource_type || filterForm.uid || filterForm.platform ||
  filterForm.status || filterForm.start_date || filterForm.end_date || filterForm.include_deleted,
)

const loadResourceTypes = async () => {
  typesLoading.value = true
  try {
    resourceTypes.value = await api.getFlashcardResourceTypes()
  } catch { /* ignore */ }
  finally { typesLoading.value = false }
}

const doSearch = async (offset = 0) => {
  loading.value = true
  error.value = ''
  currentOffset.value = offset
  try {
    results.value = await api.searchFlashcards({
      resource_type: filterForm.resource_type || undefined,
      uid: filterForm.uid || undefined,
      platform: filterForm.platform || undefined,
      status: filterForm.status || undefined,
      start_date: filterForm.start_date || undefined,
      end_date: filterForm.end_date || undefined,
      include_deleted: filterForm.include_deleted,
      limit: PAGE_SIZE,
      offset,
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '查询失败'
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filterForm.resource_type = ''
  filterForm.uid = ''
  filterForm.platform = ''
  filterForm.status = ''
  filterForm.start_date = ''
  filterForm.end_date = ''
  filterForm.include_deleted = false
  results.value = []
  error.value = ''
}

onMounted(loadResourceTypes)
</script>

<template>
  <section class="fc-page">

    <!-- 页头 -->
    <div class="panel-header">
      <div>
        <div class="panel-eyebrow">Flashcards</div>
        <h2>资源数据查询</h2>
      </div>
    </div>

    <!-- 资源类型快速选择 -->
    <div class="fc-type-bar">
      <div class="fc-type-label">资源类型</div>
      <div class="fc-type-chips" v-if="!typesLoading && resourceTypes.length">
        <button
          class="fc-type-chip"
          :class="{ selected: filterForm.resource_type === '' }"
          @click="filterForm.resource_type = ''"
        >
          全部
        </button>
        <button
          v-for="t in resourceTypes"
          :key="t.resource_type"
          class="fc-type-chip"
          :class="{ selected: filterForm.resource_type === t.resource_type }"
          :style="filterForm.resource_type === t.resource_type
            ? { background: typeColor(t.resource_type), color: '#fff', borderColor: typeColor(t.resource_type) }
            : { borderColor: typeColor(t.resource_type) + '60', color: typeTextColor(t.resource_type) }"
          @click="filterForm.resource_type = t.resource_type"
        >
          <span class="fc-type-dot" :style="{ background: typeColor(t.resource_type) }"></span>
          {{ t.resource_type }}
          <span class="fc-type-count">{{ t.count.toLocaleString() }}</span>
        </button>
      </div>
      <div v-else-if="typesLoading" class="fc-type-loading">加载资源类型…</div>
    </div>

    <!-- 过滤条件面板 -->
    <div class="fc-filter-card">
      <div class="fc-filter-row">
        <label class="bq-field bq-field--wide">
          <span class="bq-label">用户 ID (uid)</span>
          <input v-model="filterForm.uid" placeholder="输入用户 ID" class="bq-input" @keydown.enter="doSearch(0)" />
        </label>

        <label class="bq-field">
          <span class="bq-label">平台</span>
          <select v-model="filterForm.platform" class="bq-select">
            <option value="">全部</option>
            <option v-for="p in PLATFORM_OPTIONS" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>

        <label class="bq-field">
          <span class="bq-label">状态</span>
          <input v-model="filterForm.status" placeholder="如 active" class="bq-input" />
        </label>

        <label class="bq-field">
          <span class="bq-label">创建时间 从</span>
          <input type="date" v-model="filterForm.start_date" class="bq-input" />
        </label>

        <label class="bq-field">
          <span class="bq-label">创建时间 到</span>
          <input type="date" v-model="filterForm.end_date" class="bq-input" />
        </label>
      </div>

      <div class="fc-filter-actions">
        <label class="fc-check-label">
          <input type="checkbox" v-model="filterForm.include_deleted" />
          <span>包含已删除的数据</span>
        </label>
        <div class="fc-filter-btns">
          <button class="btn btn-ghost" @click="resetFilters" :disabled="loading">重置</button>
          <button class="btn btn-primary" @click="doSearch(0)" :disabled="loading || !hasFilters">
            <svg v-if="!loading" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="fc-spin">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            {{ loading ? '查询中…' : '查询' }}
          </button>
        </div>
      </div>

      <div v-if="!hasFilters" class="fc-hint">
        请至少选择一个资源类型或填写查询条件
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="bq-error-banner">{{ error }}</div>

    <!-- 结果区 -->
    <div v-if="results.length" class="fc-results">
      <div class="bq-results-header">
        <span class="bq-results-count">返回 {{ results.length }} 条记录</span>
        <div class="fc-page-nav">
          <button class="btn btn-ghost btn-sm" :disabled="currentOffset === 0 || loading" @click="doSearch(currentOffset - PAGE_SIZE)">上一页</button>
          <span class="fc-page-info">第 {{ currentOffset / PAGE_SIZE + 1 }} 页</span>
          <button class="btn btn-ghost btn-sm" :disabled="results.length < PAGE_SIZE || loading" @click="doSearch(currentOffset + PAGE_SIZE)">下一页</button>
        </div>
      </div>

      <div class="bq-table-wrap">
        <table class="bq-table fc-table">
          <thead>
            <tr>
              <th>资源类型</th>
              <th>资源名称</th>
              <th>用户 ID</th>
              <th>Deck ID</th>
              <th>平台</th>
              <th>状态</th>
              <th>来源</th>
              <th>创建时间</th>
              <th>删除时间</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, idx) in results"
              :key="idx"
              class="fc-row"
              @click="selectedItem = item"
            >
              <td>
                <span
                  v-if="item.resource_type"
                  class="fc-type-badge"
                  :style="{ background: typeBg(item.resource_type), color: typeTextColor(item.resource_type), borderColor: typeColor(item.resource_type) + '40' }"
                >{{ item.resource_type }}</span>
                <span v-else class="fc-type-badge" style="background:#f1f5f9;color:#94a3b8;border-color:#e2e8f0">—</span>
              </td>
              <td class="fc-td-name" :title="item.name ?? ''">{{ item.name || '—' }}</td>
              <td class="bq-td-mono">{{ item.uid || '—' }}</td>
              <td class="bq-td-mono">{{ item.deck_id || '—' }}</td>
              <td>
                <span v-if="item.platform" class="fc-platform-tag">{{ item.platform }}</span>
                <span v-else>—</span>
              </td>
              <td>
                <span v-if="item.status" class="fc-status-tag" :class="`fc-status--${item.status?.toLowerCase()}`">{{ item.status }}</span>
                <span v-else>—</span>
              </td>
              <td class="bq-td-mono" style="font-size:11px">{{ item.source || '—' }}</td>
              <td class="bq-td-time">{{ item.create_at?.slice(0, 16) || '—' }}</td>
              <td class="bq-td-time" :class="{ 'fc-deleted': !!item.deleted_at }">
                {{ item.deleted_at ? item.deleted_at.slice(0, 16) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="fc-page-bar">
        <button class="btn btn-ghost btn-sm" :disabled="currentOffset === 0 || loading" @click="doSearch(currentOffset - PAGE_SIZE)">← 上一页</button>
        <span class="fc-page-info">第 {{ currentOffset / PAGE_SIZE + 1 }} 页 · 每页 {{ PAGE_SIZE }} 条</span>
        <button class="btn btn-ghost btn-sm" :disabled="results.length < PAGE_SIZE || loading" @click="doSearch(currentOffset + PAGE_SIZE)">下一页 →</button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && !error" class="bq-empty">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color:var(--text-faint);margin-bottom:12px">
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
      </svg>
      <div>选择资源类型或填写条件后点击查询</div>
    </div>

    <!-- 详情弹窗 -->
    <teleport to="body">
      <div v-if="selectedItem" class="bq-lightbox" @click.self="selectedItem = null">
        <div class="bq-lightbox-content fc-detail-modal">
          <button class="bq-lightbox-close" @click="selectedItem = null">&times;</button>
          <div class="fc-detail-header">
            <span
              class="fc-type-badge fc-type-badge--lg"
              :style="{ background: typeBg(selectedItem.resource_type ?? ''), color: typeTextColor(selectedItem.resource_type ?? ''), borderColor: typeColor(selectedItem.resource_type ?? '') + '40' }"
            >{{ selectedItem.resource_type || 'UNKNOWN' }}</span>
            <div class="fc-detail-title">{{ selectedItem.name || '（无名称）' }}</div>
          </div>
          <div class="fc-detail-body">
            <div class="fc-detail-group">
              <div class="fc-detail-section-title">基本信息</div>
              <div class="bq-lightbox-row"><span class="bq-lightbox-label">用户 ID</span><span class="bq-lightbox-value bq-lightbox-mono">{{ selectedItem.uid || '—' }}</span></div>
              <div class="bq-lightbox-row"><span class="bq-lightbox-label">Deck ID</span><span class="bq-lightbox-value bq-lightbox-mono">{{ selectedItem.deck_id || '—' }}</span></div>
              <div class="bq-lightbox-row"><span class="bq-lightbox-label">平台</span><span class="bq-lightbox-value">{{ selectedItem.platform || '—' }}</span></div>
              <div class="bq-lightbox-row"><span class="bq-lightbox-label">状态</span><span class="bq-lightbox-value">{{ selectedItem.status || '—' }}</span></div>
              <div class="bq-lightbox-row"><span class="bq-lightbox-label">来源</span><span class="bq-lightbox-value">{{ selectedItem.source || '—' }}</span></div>
              <div class="bq-lightbox-row" v-if="selectedItem.selected_page_index"><span class="bq-lightbox-label">选中页码</span><span class="bq-lightbox-value">{{ selectedItem.selected_page_index }}</span></div>
            </div>
            <div class="fc-detail-group">
              <div class="fc-detail-section-title">时间</div>
              <div class="bq-lightbox-row"><span class="bq-lightbox-label">创建时间</span><span class="bq-lightbox-value">{{ selectedItem.create_at || '—' }}</span></div>
              <div class="bq-lightbox-row"><span class="bq-lightbox-label">更新时间</span><span class="bq-lightbox-value">{{ selectedItem.update_at || '—' }}</span></div>
              <div class="bq-lightbox-row" v-if="selectedItem.deleted_at">
                <span class="bq-lightbox-label">删除时间</span>
                <span class="bq-lightbox-value" style="color:var(--danger)">{{ selectedItem.deleted_at }}</span>
              </div>
            </div>
            <div v-if="selectedItem.origin_url || selectedItem.parsed_url" class="fc-detail-group">
              <div class="fc-detail-section-title">资源链接</div>
              <div v-if="selectedItem.origin_url" class="bq-lightbox-row" style="flex-direction:column;gap:4px">
                <span class="bq-lightbox-label">原始链接</span>
                <a :href="selectedItem.origin_url" target="_blank" class="fc-detail-link">{{ selectedItem.origin_url }}</a>
              </div>
              <div v-if="selectedItem.parsed_url" class="bq-lightbox-row" style="flex-direction:column;gap:4px">
                <span class="bq-lightbox-label">解析链接</span>
                <a :href="selectedItem.parsed_url" target="_blank" class="fc-detail-link">{{ selectedItem.parsed_url }}</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

<style scoped>
.fc-page { display: flex; flex-direction: column; gap: 16px; }

/* 类型栏 */
.fc-type-bar {
  display: flex; align-items: flex-start; gap: 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 16px;
}
.fc-type-label {
  font-size: 11px; font-weight: 600; color: var(--text-faint);
  text-transform: uppercase; letter-spacing: 0.3px;
  flex-shrink: 0; padding-top: 6px;
}
.fc-type-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.fc-type-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 20px;
  font-size: 12px; font-weight: 600; cursor: pointer;
  border: 1.5px solid var(--border); background: var(--bg);
  color: var(--text-muted); transition: all 0.15s;
}
.fc-type-chip:hover { box-shadow: 0 0 0 2px var(--border-focus); }
.fc-type-chip.selected { font-weight: 700; }
.fc-type-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.fc-type-count {
  font-size: 10px; opacity: 0.7; margin-left: 2px;
}
.fc-type-loading { font-size: 12px; color: var(--text-faint); padding: 4px 0; }

/* 过滤卡片 */
.fc-filter-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px;
}
.fc-filter-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.fc-filter-actions {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 8px;
}
.fc-filter-btns { display: flex; gap: 8px; align-items: center; }
.fc-check-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--text-muted); cursor: pointer;
  user-select: none;
}
.fc-check-label input[type="checkbox"] { width: 14px; height: 14px; cursor: pointer; }
.fc-hint {
  margin-top: 10px; font-size: 12px; color: var(--text-faint);
  display: flex; align-items: center; gap: 6px;
}
.fc-hint::before {
  content: '';
  width: 14px; height: 14px; flex-shrink: 0;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23CBD5E1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Cline x1='12' y1='8' x2='12' y2='12'/%3E%3Cline x1='12' y1='16' x2='12.01' y2='16'/%3E%3C/svg%3E") center/contain no-repeat;
}

/* 结果区 */
.fc-results { display: flex; flex-direction: column; gap: 12px; }
.fc-table td { cursor: pointer; }
.fc-row:hover td { background: var(--primary-light) !important; }
.fc-type-badge {
  display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: 5px;
  font-size: 11px; font-weight: 700;
  border: 1px solid transparent; white-space: nowrap;
}
.fc-type-badge--lg { font-size: 13px; padding: 4px 12px; border-radius: 7px; }
.fc-td-name {
  max-width: 200px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
  font-size: 13px; color: var(--text);
}
.fc-platform-tag {
  font-size: 11px; padding: 2px 7px; border-radius: 4px;
  background: #F0F9FF; color: #0284C7; border: 1px solid #BAE6FD;
}
.fc-status-tag {
  font-size: 11px; padding: 2px 7px; border-radius: 4px;
  background: var(--bg); color: var(--text-muted); border: 1px solid var(--border);
}
.fc-status--active { background: #F0FDF4; color: #16A34A; border-color: #BBF7D0; }
.fc-status--inactive, .fc-status--deleted { background: #FEF2F2; color: #DC2626; border-color: #FECACA; }
.fc-deleted { color: var(--danger) !important; }

.fc-page-nav { display: flex; align-items: center; gap: 8px; }
.fc-page-info { font-size: 12px; color: var(--text-faint); }
.fc-page-bar {
  display: flex; justify-content: center; align-items: center;
  gap: 16px; padding: 8px 0;
}

/* 详情弹窗 */
.fc-detail-modal { padding: 0 !important; overflow: hidden; }
.fc-detail-header {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 24px 16px; border-bottom: 1px solid var(--border);
}
.fc-detail-title {
  font-size: 15px; font-weight: 600; color: var(--text);
  flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.fc-detail-body {
  padding: 16px 24px 24px;
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
  max-height: 60vh; overflow-y: auto;
}
.fc-detail-group { display: flex; flex-direction: column; gap: 8px; }
.fc-detail-section-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.5px; color: var(--text-faint);
  margin-bottom: 4px;
}
.fc-detail-link {
  font-size: 12px; color: var(--primary); word-break: break-all;
  text-decoration: none;
}
.fc-detail-link:hover { text-decoration: underline; }

@keyframes fc-spin { to { transform: rotate(360deg); } }
.fc-spin { animation: fc-spin 0.8s linear infinite; }

/* 复用 bq 样式 */
.bq-field { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 140px; }
.bq-field--wide { min-width: 200px; }
.bq-label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.3px; }
.bq-input, .bq-select {
  padding: 7px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: 13px; background: var(--bg); color: var(--text);
  transition: border-color 0.15s;
}
.bq-input:focus, .bq-select:focus { border-color: var(--border-focus); outline: none; }
.bq-error-banner {
  padding: 10px 14px; background: var(--danger-light); color: var(--danger);
  border-radius: 8px; font-size: 13px;
}
.bq-results-header { display: flex; align-items: center; justify-content: space-between; }
.bq-results-count { font-size: 12px; color: var(--text-faint); font-weight: 600; }
.bq-table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
.bq-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.bq-table th { text-align: left; padding: 10px 12px; background: var(--bg); font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.3px; border-bottom: 1px solid var(--border); white-space: nowrap; }
.bq-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.bq-table tr:last-child td { border-bottom: none; }
.bq-td-mono { font-family: monospace; font-size: 12px; color: var(--text-muted); white-space: nowrap; max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
.bq-td-time { white-space: nowrap; font-size: 12px; color: var(--text-faint); }
.bq-empty { text-align: center; padding: 64px 0; color: var(--text-faint); font-size: 13px; display: flex; flex-direction: column; align-items: center; }
.bq-lightbox { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,0.55); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; padding: 24px; }
.bq-lightbox-content { background: var(--surface, #fff); border-radius: 14px; max-width: 680px; width: 100%; max-height: 90vh; overflow-y: auto; box-shadow: 0 24px 64px rgba(0,0,0,0.2); position: relative; }
.bq-lightbox-close { position: absolute; top: 12px; right: 14px; z-index: 1; width: 30px; height: 30px; border-radius: 8px; border: none; background: var(--bg, #f1f5f9); color: var(--text-muted); font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.bq-lightbox-close:hover { background: var(--border); }
.bq-lightbox-row { display: flex; gap: 8px; align-items: baseline; }
.bq-lightbox-label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.3px; min-width: 72px; flex-shrink: 0; }
.bq-lightbox-value { font-size: 13px; color: var(--text); }
.bq-lightbox-mono { font-family: monospace; font-size: 12px; }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: 1px solid transparent; transition: all 0.15s; }
.btn-primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.btn-primary:hover:not(:disabled) { background: var(--primary-hover, #4338CA); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost { background: none; color: var(--text-muted); border-color: var(--border); }
.btn-ghost:hover:not(:disabled) { background: var(--bg); }
.btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-sm { padding: 5px 12px; font-size: 12px; }
</style>
