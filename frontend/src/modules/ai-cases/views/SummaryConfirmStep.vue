<script setup lang="ts">
import { computed } from 'vue'
import type { ClarificationGap, ClarificationQuestion, StructuredSummary } from '../types'

const props = defineProps<{
  summary: StructuredSummary
  clarificationQuestions: ClarificationQuestion[]
  clarificationDraftAnswers: Record<string, string>
  missingFields: ClarificationGap[]
  remainingRisks: string[]
  isComplete: boolean
  hasUnansweredBlocking: boolean
  loadingRefine: boolean
  loadingGenerate: boolean
}>()

const emit = defineEmits<{
  refine: []
  generateDesign: []
}>()

const hasAnyAnswer = computed(() =>
  props.clarificationQuestions.some(q => (props.clarificationDraftAnswers[q.id] || '').trim())
)

const hasExperimentGroups = computed(() => props.summary.experiment_groups?.length > 0)
const alerts = computed(() => [
  ...props.missingFields.map(f => ({ type: 'gap' as const, text: `${f.field}：${f.detail}` })),
  ...props.remainingRisks.map(r => ({ type: 'risk' as const, text: r })),
])

const listToText = (value: string[]) => value.join('\n')
const textToList = (value: string) =>
  value.split('\n').map(item => item.trim()).filter(Boolean)
</script>

<template>
  <div class="sc-layout">

    <!-- ── Left: Summary Editor ── -->
    <div class="sc-main">
      <div class="sc-main-header">
        <div class="sc-eyebrow">Step 2 · 摘要确认</div>
        <h2 class="sc-title">核对 AI 解析的需求摘要</h2>
      </div>

      <!-- 标题 + 业务目标（一行） -->
      <div class="sc-section">
        <div class="sc-row-2">
          <label class="sc-field">
            <span class="sc-field-label">功能标题</span>
            <input class="sc-input" v-model="summary.title" placeholder="例：用户登录功能" />
          </label>
          <label class="sc-field">
            <span class="sc-field-label">业务目标</span>
            <input class="sc-input" v-model="summary.business_goal" placeholder="该功能要解决什么问题" />
          </label>
        </div>
      </div>

      <!-- 参与角色 -->
      <div class="sc-section">
        <label class="sc-field">
          <span class="sc-field-label">参与角色 <span class="sc-field-hint">每行一个</span></span>
          <textarea
            class="sc-textarea"
            rows="3"
            placeholder="例：注册用户&#10;管理员&#10;游客"
            :value="listToText(summary.actors)"
            @input="summary.actors = textToList(($event.target as HTMLTextAreaElement).value)"
          ></textarea>
        </label>
      </div>

      <!-- 通用流程（无实验组时展示全部，有实验组时展示共享部分） -->
      <div class="sc-section">
        <div class="sc-section-label">
          {{ hasExperimentGroups ? '通用流程（各实验组共享）' : '主流程' }}
        </div>
        <label class="sc-field">
          <span class="sc-field-label">正向操作路径 <span class="sc-field-hint">每行一步</span></span>
          <textarea
            class="sc-textarea sc-textarea--flow"
            rows="6"
            placeholder="1. 用户进入页面&#10;2. 执行核心操作&#10;3. 系统返回结果"
            :value="listToText(summary.main_flow)"
            @input="summary.main_flow = textToList(($event.target as HTMLTextAreaElement).value)"
          ></textarea>
        </label>
        <label class="sc-field" style="margin-top:8px">
          <span class="sc-field-label">异常路径 <span class="sc-field-hint">每行一个场景</span></span>
          <textarea
            class="sc-textarea"
            rows="4"
            placeholder="密码错误超过 5 次，账号锁定&#10;网络超时，提示重试"
            :value="listToText(summary.exception_flows)"
            @input="summary.exception_flows = textToList(($event.target as HTMLTextAreaElement).value)"
          ></textarea>
        </label>
        <label class="sc-field" style="margin-top:8px">
          <span class="sc-field-label">业务规则 <span class="sc-field-hint">每行一条</span></span>
          <textarea
            class="sc-textarea"
            rows="4"
            placeholder="密码至少 8 位，包含数字和字母&#10;每日限购 3 件"
            :value="listToText(summary.business_rules)"
            @input="summary.business_rules = textToList(($event.target as HTMLTextAreaElement).value)"
          ></textarea>
        </label>
      </div>

      <!-- 实验分组（有分组时展示） -->
      <div v-if="hasExperimentGroups" class="sc-section">
        <div class="sc-section-label">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><path d="M20 8v6"/><path d="M23 11h-6"/>
          </svg>
          实验分组
        </div>
        <div v-for="(group, idx) in summary.experiment_groups" :key="idx" class="sc-group-card">
          <div class="sc-group-header">
            <input class="sc-group-name" v-model="group.name" placeholder="实验组名称" />
            <input class="sc-group-desc" v-model="group.description" placeholder="简要描述该组特点" />
          </div>
          <label class="sc-field">
            <span class="sc-field-label">该组主流程 <span class="sc-field-hint">与通用流程的差异部分</span></span>
            <textarea
              class="sc-textarea"
              rows="4"
              :value="listToText(group.main_flow)"
              @input="group.main_flow = textToList(($event.target as HTMLTextAreaElement).value)"
              placeholder="该实验组独有的流程步骤"
            ></textarea>
          </label>
          <label class="sc-field" style="margin-top:6px">
            <span class="sc-field-label">该组异常路径</span>
            <textarea
              class="sc-textarea"
              rows="3"
              :value="listToText(group.exception_flows)"
              @input="group.exception_flows = textToList(($event.target as HTMLTextAreaElement).value)"
              placeholder="该实验组独有的异常场景"
            ></textarea>
          </label>
          <label class="sc-field" style="margin-top:6px">
            <span class="sc-field-label">该组业务规则</span>
            <textarea
              class="sc-textarea"
              rows="3"
              :value="listToText(group.business_rules)"
              @input="group.business_rules = textToList(($event.target as HTMLTextAreaElement).value)"
              placeholder="该实验组独有的规则"
            ></textarea>
          </label>
        </div>
      </div>
    </div>

    <!-- ── Right: AI Analysis Panel ── -->
    <div class="sc-side">

      <!-- Status -->
      <div class="sc-status" :class="isComplete ? 'sc-status--ok' : hasUnansweredBlocking ? 'sc-status--block' : 'sc-status--ok'">
        <div class="sc-status-icon">
          <svg v-if="hasUnansweredBlocking" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <div>
          <div class="sc-status-title">{{ isComplete ? '需求信息已就绪' : hasUnansweredBlocking ? '有阻塞问题待确认' : '可以进入测试设计' }}</div>
          <div class="sc-status-sub">{{ isComplete ? 'AI 判定信息足够支撑测试设计' : hasUnansweredBlocking ? '建议回答标红问题以提高覆盖质量' : '所有关键信息已齐备' }}</div>
        </div>
      </div>

      <!-- Clarification Questions -->
      <div v-if="clarificationQuestions.length > 0" class="sc-side-section">
        <div class="sc-side-label">AI 澄清问题</div>
        <div class="sc-questions">
          <div v-for="q in clarificationQuestions" :key="q.id" class="sc-question" :class="{ 'sc-question--blocking': q.blocking }">
            <div class="sc-question-top">
              <span class="sc-question-text">{{ q.question }}</span>
              <span class="sc-q-badge" :class="q.blocking ? 'sc-q-badge--block' : 'sc-q-badge--suggest'">
                {{ q.blocking ? '阻塞' : '建议' }}
              </span>
            </div>
            <div class="sc-question-reason">{{ q.reason }}</div>
            <textarea class="sc-textarea sc-q-answer" rows="2" placeholder="填写确认、假设或补充信息…" v-model="clarificationDraftAnswers[q.id]"></textarea>
          </div>
        </div>
      </div>
      <div v-else class="sc-side-section">
        <div class="sc-side-label">AI 澄清问题</div>
        <div class="sc-empty-hint">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          没有澄清问题
        </div>
      </div>

      <!-- Alerts (merged gaps + risks) -->
      <div v-if="alerts.length" class="sc-side-section">
        <div class="sc-side-label">需要关注</div>
        <div class="sc-alert-list">
          <div v-for="(a, idx) in alerts" :key="idx" class="sc-alert-item">
            <span class="sc-alert-dot" :class="a.type === 'gap' ? 'sc-alert-dot--gap' : 'sc-alert-dot--risk'"></span>
            {{ a.text }}
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="sc-actions">
        <button class="btn btn-primary sc-btn-generate" :disabled="loadingGenerate" @click="emit('generateDesign')">
          <svg v-if="!loadingGenerate" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          {{ loadingGenerate ? '生成中…' : '确认生成测试设计' }}
        </button>
        <button
          v-if="clarificationQuestions.length > 0"
          class="btn btn-default sc-btn-refine"
          :disabled="loadingRefine || !hasAnyAnswer"
          @click="emit('refine')"
        >
          {{ loadingRefine ? '更新中…' : '结合回答重新整理摘要' }}
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
.sc-group-card {
  border: 1px solid var(--primary-border);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
  background: var(--primary-light);
}
.sc-group-header {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}
.sc-group-name {
  flex: 0 0 200px;
  font-size: 14px;
  font-weight: 700;
  color: var(--primary);
  border: 1px solid var(--primary-border);
  border-radius: 6px;
  padding: 5px 10px;
  background: white;
}
.sc-group-desc {
  flex: 1;
  font-size: 13px;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  background: white;
}
.sc-alert-list { display: flex; flex-direction: column; gap: 6px; }
.sc-alert-item { font-size: 12px; color: var(--text-sub); display: flex; align-items: flex-start; gap: 6px; line-height: 1.5; }
.sc-alert-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 5px; }
.sc-alert-dot--gap { background: var(--warning); }
.sc-alert-dot--risk { background: var(--danger); }
</style>
