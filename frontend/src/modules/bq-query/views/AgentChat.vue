<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { createBqApi } from '../api'
import type { AgentChatMessage, AgentResponse } from '../types'

const props = defineProps<{ apiBaseUrl: string; sourceKey: string }>()
const api = createBqApi(props.apiBaseUrl)

const input = ref('')
const loading = ref(false)
const messages = ref<{ role: 'user' | 'model'; content: string; results?: any[]; resultType?: string | null }[]>([])
const msgListRef = ref<HTMLElement | null>(null)

const examples = [
  '帮我查一下英文数学题的图片',
  '查询 question_id 为 xxx 的题目',
  '有哪些可用的学科？',
  '最近一周的物理题有多少',
]

const scrollToBottom = () => {
  nextTick(() => { if (msgListRef.value) msgListRef.value.scrollTop = msgListRef.value.scrollHeight })
}

const sendMessage = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  scrollToBottom()
  loading.value = true
  try {
    const history: AgentChatMessage[] = messages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content }))
    const result: AgentResponse = await api.agentChat(props.sourceKey, text, history)
    messages.value.push({ role: 'model', content: result.reply, results: result.results || undefined, resultType: result.result_type })
  } catch (e) {
    messages.value.push({ role: 'model', content: `错误：${e instanceof Error ? e.message : '未知错误'}` })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const useExample = (ex: string) => { input.value = ex; sendMessage() }
const clearHistory = () => { messages.value = [] }
</script>

<template>
  <section class="panel agent-panel">
    <div class="panel-header">
      <div>
        <div class="panel-eyebrow">BQ 数据查询</div>
        <h2>AI 智能查询</h2>
      </div>
      <button v-if="messages.length" class="btn btn-ghost" @click="clearHistory">清空对话</button>
    </div>

    <!-- Chat Area -->
    <div class="agent-body" ref="msgListRef">
      <!-- Welcome -->
      <div v-if="messages.length === 0" class="agent-welcome">
        <div class="agent-welcome-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
        </div>
        <div class="agent-welcome-title">Solvely 数据助手</div>
        <div class="agent-welcome-desc">用自然语言查询 BigQuery 数据</div>
        <div class="agent-examples">
          <button v-for="ex in examples" :key="ex" class="agent-example" @click="useExample(ex)">{{ ex }}</button>
        </div>
      </div>

      <!-- Messages -->
      <div v-for="(msg, idx) in messages" :key="idx" class="agent-msg" :class="msg.role">
        <div class="agent-avatar">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
        <div class="agent-bubble">
          <div class="agent-text">{{ msg.content }}</div>
          <!-- Inline Results -->
          <div v-if="msg.results && msg.results.length" class="agent-inline-results">
            <div class="agent-inline-count">{{ msg.results.length }} 条结果</div>
            <div v-if="msg.resultType === 'pictures'" class="agent-pic-grid">
              <div v-for="(item, i) in msg.results.slice(0, 12)" :key="i" class="agent-pic">
                <img v-if="item.image_url" :src="item.image_url" loading="lazy" />
                <div class="agent-pic-label">{{ item.subject || '' }} · {{ item.language || '' }}</div>
              </div>
            </div>
            <div v-else class="agent-data-list">
              <div v-for="(item, i) in msg.results.slice(0, 10)" :key="i" class="agent-data-row">
                <span class="agent-data-id">{{ item.question_id || item.device_id || '-' }}</span>
                <span class="agent-data-text">{{ (item.question_text || item.subject || '').slice(0, 60) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="agent-msg model">
        <div class="agent-avatar">AI</div>
        <div class="agent-bubble agent-bubble--loading">
          <span class="agent-dot"></span><span class="agent-dot"></span><span class="agent-dot"></span>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="agent-footer">
      <input
        v-model="input"
        class="agent-input"
        placeholder="输入查询，如：查一下英文数学题最近一周的图片"
        @keydown.enter="sendMessage"
        :disabled="loading"
      />
      <button class="btn btn-primary agent-send" :disabled="loading || !input.trim()" @click="sendMessage">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
  </section>
</template>

<style scoped>
.agent-panel { display: flex; flex-direction: column; min-height: 0; }

.agent-body {
  flex: 1; overflow-y: auto; padding: 16px 0;
  display: flex; flex-direction: column; gap: 16px;
  min-height: 400px; max-height: calc(100vh - 260px);
}

/* Welcome */
.agent-welcome { display: flex; flex-direction: column; align-items: center; padding: 48px 0; }
.agent-welcome-icon { width: 56px; height: 56px; border-radius: 14px; background: var(--primary-light); display: flex; align-items: center; justify-content: center; margin-bottom: 16px; }
.agent-welcome-title { font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.agent-welcome-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 20px; }
.agent-examples { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 460px; }
.agent-example {
  padding: 7px 16px; border-radius: 20px; font-size: 12px; cursor: pointer;
  background: var(--surface); border: 1px solid var(--border); color: var(--text-sub);
  transition: all 0.15s;
}
.agent-example:hover { border-color: var(--primary-border); color: var(--primary); background: var(--primary-light); }

/* Messages */
.agent-msg { display: flex; gap: 10px; align-items: flex-start; }
.agent-msg.user { flex-direction: row-reverse; }
.agent-avatar {
  width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
}
.agent-msg.user .agent-avatar { background: var(--primary); color: white; }
.agent-msg.model .agent-avatar { background: var(--bg); color: var(--text-muted); border: 1px solid var(--border); }

.agent-bubble {
  max-width: 75%; padding: 10px 14px; border-radius: 12px;
  font-size: 13px; line-height: 1.65;
}
.agent-msg.user .agent-bubble { background: var(--primary); color: white; border-top-right-radius: 4px; }
.agent-msg.model .agent-bubble { background: var(--surface); border: 1px solid var(--border); border-top-left-radius: 4px; }

.agent-bubble--loading { display: flex; gap: 4px; align-items: center; padding: 12px 18px; }
.agent-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-faint); animation: dotPulse 1.2s infinite; }
.agent-dot:nth-child(2) { animation-delay: 0.2s; }
.agent-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotPulse { 0%, 80%, 100% { opacity: 0.3; } 40% { opacity: 1; } }

/* Inline Results */
.agent-inline-results { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border); }
.agent-inline-count { font-size: 11px; color: var(--text-faint); margin-bottom: 8px; }
.agent-pic-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 6px; }
.agent-pic { border-radius: 6px; overflow: hidden; border: 1px solid var(--border); }
.agent-pic img { width: 100%; height: 72px; object-fit: cover; display: block; }
.agent-pic-label { padding: 3px 6px; font-size: 10px; color: var(--text-faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.agent-data-list { display: flex; flex-direction: column; gap: 4px; }
.agent-data-row { display: flex; gap: 8px; align-items: baseline; padding: 4px 8px; background: var(--bg); border-radius: 4px; font-size: 12px; }
.agent-data-id { font-family: monospace; color: var(--text-faint); flex-shrink: 0; font-size: 11px; }
.agent-data-text { color: var(--text-sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Footer */
.agent-footer {
  display: flex; gap: 8px; padding: 14px 0 0; border-top: 1px solid var(--border); margin-top: auto;
}
.agent-input {
  flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 10px;
  font-size: 13px; background: var(--surface); color: var(--text);
  transition: border-color 0.15s;
}
.agent-input:focus { border-color: var(--border-focus); outline: none; }
.agent-send { padding: 10px 14px; border-radius: 10px; }
</style>
