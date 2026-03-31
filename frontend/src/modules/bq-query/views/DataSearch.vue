<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { createBqApi } from '../api'
import type { PictureItem, QuestionDetail, FilterOptions } from '../types'
import FlashcardsSearch from './FlashcardsSearch.vue'

const props = defineProps<{ apiBaseUrl: string; sourceKey: string }>()
const api = createBqApi(props.apiBaseUrl)

const mode = ref<'filter' | 'id'>('filter')
const loading = ref(false)
const error = ref('')
const options = ref<FilterOptions>({ languages: [], subjects: [], task_types: [] })
const optLoading = ref(false)
const pictures = ref<PictureItem[]>([])
const questions = ref<QuestionDetail[]>([])
const selectedItem = ref<PictureItem | QuestionDetail | null>(null)
const filterForm = reactive({
  language: '',
  subject: '',
  task_type: '',
  start_date: '',
  end_date: '',
  limit: 50,
})

const idForm = reactive({
  question_id: '',
  device_id: '',
  limit: 20,
})

const loadOptions = async () => {
  optLoading.value = true
  try { options.value = await api.getFilterOptions(props.sourceKey) } catch { /* ignore */ }
  finally { optLoading.value = false }
}

const searchPictures = async () => {
  loading.value = true; error.value = ''; pictures.value = []
  try {
    pictures.value = await api.searchPictures(props.sourceKey, {
      language: filterForm.language || undefined,
      subject: filterForm.subject || undefined,
      task_type: filterForm.task_type || undefined,
      start_date: filterForm.start_date || undefined,
      end_date: filterForm.end_date || undefined,
      limit: filterForm.limit,
    })
  } catch (e) { error.value = e instanceof Error ? e.message : '查询失败' }
  finally { loading.value = false }
}

const lookupById = async () => {
  loading.value = true; error.value = ''; questions.value = []
  try {
    questions.value = await api.lookupQuestion(props.sourceKey, {
      question_id: idForm.question_id || undefined,
      device_id: idForm.device_id || undefined,
      limit: idForm.limit,
    })
  } catch (e) { error.value = e instanceof Error ? e.message : '查询失败' }
  finally { loading.value = false }
}

loadOptions()
watch(() => props.sourceKey, () => { pictures.value = []; questions.value = []; loadOptions() })
</script>

<template>
  <!-- Flashcards 使用专属查询页 -->
  <FlashcardsSearch v-if="props.sourceKey === 'flashcards'" :api-base-url="props.apiBaseUrl" />

  <section v-else class="panel">
    <!-- Header -->
    <div class="panel-header">
      <div>
        <div class="panel-eyebrow">BQ 数据查询</div>
        <h2>条件筛选 & ID 查询</h2>
      </div>
    </div>

    <!-- Mode Switch -->
    <div class="bq-tabs">
      <button class="bq-tab" :class="{ active: mode === 'filter' }" @click="mode = 'filter'">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
        条件筛选
      </button>
      <button class="bq-tab" :class="{ active: mode === 'id' }" @click="mode = 'id'">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        ID 查询
      </button>
    </div>

    <!-- Filter Form -->
    <div v-if="mode === 'filter'" class="bq-card">
      <div class="bq-form-row">
        <label class="bq-field">
          <span class="bq-label">语言</span>
          <select v-model="filterForm.language" class="bq-select">
            <option value="">全部</option>
            <option v-for="l in options.languages" :key="l" :value="l">{{ l }}</option>
          </select>
        </label>
        <label class="bq-field">
          <span class="bq-label">学科</span>
          <select v-model="filterForm.subject" class="bq-select">
            <option value="">全部</option>
            <option v-for="s in options.subjects" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
        <label class="bq-field">
          <span class="bq-label">任务类型</span>
          <select v-model="filterForm.task_type" class="bq-select">
            <option value="">全部</option>
            <option v-for="t in options.task_types" :key="t" :value="t">{{ t }}</option>
          </select>
        </label>
      </div>
      <div class="bq-form-row">
        <label class="bq-field">
          <span class="bq-label">开始日期</span>
          <input type="date" v-model="filterForm.start_date" class="bq-input" />
        </label>
        <label class="bq-field">
          <span class="bq-label">结束日期</span>
          <input type="date" v-model="filterForm.end_date" class="bq-input" />
        </label>
        <label class="bq-field bq-field--narrow">
          <span class="bq-label">条数</span>
          <input type="number" v-model.number="filterForm.limit" min="1" max="100" class="bq-input" />
        </label>
        <div class="bq-field bq-field--action">
          <button class="btn btn-primary" :disabled="loading" @click="searchPictures">
            {{ loading ? '查询中...' : '查询' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ID Form -->
    <div v-else class="bq-card">
      <div class="bq-form-row">
        <label class="bq-field bq-field--wide">
          <span class="bq-label">Question ID</span>
          <input v-model="idForm.question_id" placeholder="输入题目 ID" class="bq-input" />
        </label>
        <label class="bq-field bq-field--wide">
          <span class="bq-label">Device ID</span>
          <input v-model="idForm.device_id" placeholder="输入设备 ID" class="bq-input" />
        </label>
        <label class="bq-field bq-field--narrow">
          <span class="bq-label">条数</span>
          <input type="number" v-model.number="idForm.limit" min="1" max="100" class="bq-input" />
        </label>
        <div class="bq-field bq-field--action">
          <button class="btn btn-primary" :disabled="loading" @click="lookupById">
            {{ loading ? '查询中...' : '查询' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="bq-error-banner">{{ error }}</div>

    <!-- Picture Results -->
    <div v-if="mode === 'filter' && pictures.length" class="bq-results">
      <div class="bq-results-header">
        <span class="bq-results-count">{{ pictures.length }} 条结果</span>
      </div>
      <div class="bq-grid">
        <div v-for="(item, idx) in pictures" :key="idx" class="bq-img-card" @click="selectedItem = item">
          <div class="bq-img-wrap">
            <img v-if="item.image_url" :src="item.image_url" loading="lazy" />
            <div v-else class="bq-img-placeholder">无图片</div>
          </div>
          <div class="bq-img-info">
            <div class="bq-img-id">{{ item.question_id }}</div>
            <div class="bq-img-tags">
              <span v-if="item.subject" class="bq-tag">{{ item.subject }}</span>
              <span v-if="item.language" class="bq-tag">{{ item.language }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Question Results -->
    <div v-if="mode === 'id' && questions.length" class="bq-results">
      <div class="bq-results-header">
        <span class="bq-results-count">{{ questions.length }} 条结果</span>
      </div>
      <div class="bq-table-wrap">
        <table class="bq-table">
          <thead>
            <tr>
              <th>Question ID</th>
              <th>Device ID</th>
              <th>学科</th>
              <th>语言</th>
              <th>题目文本</th>
              <th>答案</th>
              <th>时间</th>
              <th>图片</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in questions" :key="idx">
              <td class="bq-td-mono">{{ item.question_id }}</td>
              <td class="bq-td-mono">{{ item.device_id }}</td>
              <td>{{ item.subject }}</td>
              <td>{{ item.language }}</td>
              <td class="bq-td-text">{{ item.question_text?.slice(0, 100) }}</td>
              <td class="bq-td-text">{{ item.answer?.slice(0, 80) }}</td>
              <td class="bq-td-time">{{ item.create_time }}</td>
              <td>
                <img v-if="item.image_url" :src="item.image_url" class="bq-thumb" loading="lazy" @click="selectedItem = item" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && !error && ((mode === 'filter' && !pictures.length) || (mode === 'id' && !questions.length))" class="bq-empty">
      设置查询条件后点击查询
    </div>

    <!-- Lightbox -->
    <teleport to="body">
      <div v-if="selectedItem" class="bq-lightbox" @click.self="selectedItem = null">
        <div class="bq-lightbox-content">
          <button class="bq-lightbox-close" @click="selectedItem = null">&times;</button>
          <div class="bq-lightbox-img">
            <img v-if="selectedItem.image_url" :src="selectedItem.image_url" />
            <div v-else class="bq-img-placeholder">无图片</div>
          </div>
          <div class="bq-lightbox-detail">
            <div class="bq-lightbox-row" v-if="selectedItem.question_id">
              <span class="bq-lightbox-label">Question ID</span>
              <span class="bq-lightbox-value bq-lightbox-mono">{{ selectedItem.question_id }}</span>
            </div>
            <div class="bq-lightbox-row" v-if="'device_id' in selectedItem && selectedItem.device_id">
              <span class="bq-lightbox-label">Device ID</span>
              <span class="bq-lightbox-value bq-lightbox-mono">{{ selectedItem.device_id }}</span>
            </div>
            <div class="bq-lightbox-row" v-if="selectedItem.subject">
              <span class="bq-lightbox-label">学科</span>
              <span class="bq-lightbox-value">{{ selectedItem.subject }}</span>
            </div>
            <div class="bq-lightbox-row" v-if="selectedItem.language">
              <span class="bq-lightbox-label">语言</span>
              <span class="bq-lightbox-value">{{ selectedItem.language }}</span>
            </div>
            <div class="bq-lightbox-row" v-if="selectedItem.task_type">
              <span class="bq-lightbox-label">任务类型</span>
              <span class="bq-lightbox-value">{{ selectedItem.task_type }}</span>
            </div>
            <div class="bq-lightbox-row" v-if="selectedItem.create_time">
              <span class="bq-lightbox-label">创建时间</span>
              <span class="bq-lightbox-value">{{ selectedItem.create_time }}</span>
            </div>
            <div v-if="'question_text' in selectedItem && selectedItem.question_text" class="bq-lightbox-block">
              <span class="bq-lightbox-label">题目文本</span>
              <p>{{ selectedItem.question_text }}</p>
            </div>
            <div v-if="'answer' in selectedItem && selectedItem.answer" class="bq-lightbox-block">
              <span class="bq-lightbox-label">答案</span>
              <p class="bq-lightbox-answer">{{ selectedItem.answer }}</p>
            </div>
            <div class="bq-lightbox-row" v-if="selectedItem.picture_key">
              <span class="bq-lightbox-label">Picture Key</span>
              <span class="bq-lightbox-value bq-lightbox-mono" style="font-size:11px;word-break:break-all">{{ selectedItem.picture_key }}</span>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

<style scoped>
.bq-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
.bq-tab {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  border: 1px solid transparent; background: none; color: var(--text-muted);
  transition: all 0.15s;
}
.bq-tab:hover { background: var(--bg); }
.bq-tab.active { background: var(--primary-light); color: var(--primary); border-color: var(--primary-border); }

.bq-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  padding: 16px; margin-bottom: 16px;
}
.bq-form-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
.bq-form-row:last-child { margin-bottom: 0; }
.bq-field { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 140px; }
.bq-field--narrow { max-width: 100px; min-width: 80px; flex: 0 0 auto; }
.bq-field--wide { min-width: 200px; }
.bq-field--action { display: flex; align-items: flex-end; flex: 0 0 auto; }
.bq-label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.3px; }
.bq-input, .bq-select {
  padding: 7px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: 13px; background: var(--bg); color: var(--text);
  transition: border-color 0.15s;
}
.bq-input:focus, .bq-select:focus { border-color: var(--border-focus); outline: none; }

.bq-error-banner {
  padding: 10px 14px; background: var(--danger-light); color: var(--danger);
  border-radius: 8px; font-size: 13px; margin-bottom: 16px;
}

.bq-results { margin-top: 8px; }
.bq-results-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.bq-results-count { font-size: 12px; color: var(--text-faint); font-weight: 600; }

.bq-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
@media (max-width: 1200px) { .bq-grid { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 900px) { .bq-grid { grid-template-columns: repeat(3, 1fr); } }
.bq-img-card { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--surface); transition: box-shadow 0.15s; cursor: pointer; }
.bq-img-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.bq-img-wrap { height: 160px; background: var(--bg); overflow: hidden; }
.bq-img-wrap img { width: 100%; height: 100%; object-fit: cover; }
.bq-img-placeholder { height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-faint); font-size: 12px; }
.bq-img-info { padding: 10px 12px; }
.bq-img-id { font-size: 11px; font-family: monospace; color: var(--text-faint); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bq-img-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 4px; }
.bq-tag { font-size: 11px; padding: 1px 8px; border-radius: 4px; background: var(--primary-light); color: var(--primary); }
.bq-tag--muted { background: var(--bg); color: var(--text-muted); }
.bq-img-time { font-size: 11px; color: var(--text-faint); }

.bq-table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
.bq-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.bq-table th { text-align: left; padding: 10px 12px; background: var(--bg); font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.3px; border-bottom: 1px solid var(--border); white-space: nowrap; }
.bq-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
.bq-table tr:last-child td { border-bottom: none; }
.bq-table tr:hover td { background: var(--bg); }
.bq-td-mono { font-family: monospace; font-size: 12px; color: var(--text-muted); white-space: nowrap; }
.bq-td-text { max-width: 240px; line-height: 1.5; color: var(--text-sub); }
.bq-td-time { white-space: nowrap; font-size: 12px; color: var(--text-faint); }
.bq-thumb { width: 48px; height: 48px; object-fit: cover; border-radius: 4px; cursor: pointer; }
.bq-thumb:hover { opacity: 0.8; }

.bq-empty { text-align: center; padding: 48px 0; color: var(--text-faint); font-size: 13px; }
/* Lightbox */
.bq-lightbox {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}
.bq-lightbox-content {
  background: var(--surface, #fff); border-radius: 14px;
  max-width: 720px; width: 100%; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 24px 64px rgba(0,0,0,0.2);
  position: relative;
}
.bq-lightbox-close {
  position: absolute; top: 12px; right: 14px; z-index: 1;
  width: 30px; height: 30px; border-radius: 8px;
  border: none; background: var(--bg, #f1f5f9); color: var(--text-muted);
  font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.bq-lightbox-close:hover { background: var(--border); }
.bq-lightbox-img { background: #f8fafc; display: flex; align-items: center; justify-content: center; }
.bq-lightbox-img img { width: 100%; max-height: 50vh; object-fit: contain; }
.bq-lightbox-detail { padding: 20px; display: flex; flex-direction: column; gap: 8px; }
.bq-lightbox-row { display: flex; gap: 8px; align-items: baseline; }
.bq-lightbox-label { font-size: 11px; font-weight: 600; color: var(--text-faint); text-transform: uppercase; letter-spacing: 0.3px; min-width: 80px; flex-shrink: 0; }
.bq-lightbox-value { font-size: 13px; color: var(--text); }
.bq-lightbox-mono { font-family: monospace; font-size: 12px; }
.bq-lightbox-block { margin-top: 4px; }
.bq-lightbox-block p { margin: 4px 0 0; font-size: 13px; line-height: 1.7; color: var(--text-sub); }
.bq-lightbox-answer { color: var(--success) !important; }
</style>
