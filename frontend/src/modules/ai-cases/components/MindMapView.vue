<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, nextTick, computed } from 'vue'
import MindElixir from 'mind-elixir'
import 'mind-elixir/style.css'
import { categoryLabels } from '../types'
import type { IntegrationTest, StructuredSummary, TestCase, TestPoint } from '../types'

interface MindMapNode {
  topic: string
  children?: MindMapNode[]
}

const props = defineProps<{
  apiBaseUrl: string
  platform: string
  summary: StructuredSummary
  functions: string[]
  testPoints: TestPoint[]
  cases: TestCase[]
  integrationTests: IntegrationTest[]
}>()

const containerRef = ref<HTMLElement | null>(null)
const copied = ref(false)
let meInstance: InstanceType<typeof MindElixir> | null = null

// 从 function_module 或 title 中提取实验组标记
const extractGroup = (module: string, title: string): { group: string; cleanModule: string; cleanTitle: string } => {
  const modMatch = module.match(/[-—]\s*(实验组\S+|对照组\S+|[A-Z]组)$/i)
  if (modMatch) return { group: modMatch[1], cleanModule: module.replace(modMatch[0], '').trim(), cleanTitle: title }
  const titleMatch = title.match(/^\[([^\]]*(?:实验组|对照组|[A-Z]组)[^\]]*)\]\s*/)
  if (titleMatch) return { group: titleMatch[1], cleanModule: module, cleanTitle: title.replace(titleMatch[0], '') }
  const commonMatch = title.match(/^\[通用\]\s*/)
  if (commonMatch) return { group: '通用', cleanModule: module, cleanTitle: title.replace(commonMatch[0], '') }
  return { group: '', cleanModule: module, cleanTitle: title }
}

const coverageTree = computed<MindMapNode>(() => {
  const root: MindMapNode = { topic: props.summary.title || '测试覆盖', children: [] }
  const hasCases = props.cases.length > 0
  const caseTypeLabels: Record<string, string> = {
    functional: '功能验证', boundary: '边界值', exception: '异常处理',
    permission: '权限控制', platform: '平台专项', integration: '联动测试',
  }

  // 通用构建函数
  type AnyItem = { function_module?: string; title: string; category?: string; case_type?: string; expected_results?: string[]; description?: string }
  const buildTree = (items: AnyItem[], isCase: boolean) => {
    const grouped: Record<string, Record<string, Record<string, AnyItem[]>>> = {}
    const ungrouped: Record<string, Record<string, AnyItem[]>> = {}
    let hasGroups = false

    for (const item of items) {
      const mod = (item as any).function_module || '未归类'
      const { group, cleanModule } = extractGroup(mod, item.title)
      const cat = isCase ? ((item as any).case_type || 'functional') : ((item as any).category || 'positive')
      if (group) {
        hasGroups = true
        if (!grouped[group]) grouped[group] = {}
        if (!grouped[group][cleanModule]) grouped[group][cleanModule] = {}
        if (!grouped[group][cleanModule][cat]) grouped[group][cleanModule][cat] = []
        grouped[group][cleanModule][cat].push(item)
      } else {
        if (!ungrouped[mod]) ungrouped[mod] = {}
        if (!ungrouped[mod][cat]) ungrouped[mod][cat] = []
        ungrouped[mod][cat].push(item)
      }
    }

    const buildLeaf = (item: AnyItem): MindMapNode => {
      const { cleanTitle } = extractGroup((item as any).function_module || '', item.title)
      const t = cleanTitle || item.title
      if (isCase && (item as any).expected_results?.length) {
        return { topic: t, children: (item as any).expected_results.map((r: string) => ({ topic: r })) }
      }
      const desc = (item as any).description?.split(/[。；;]/)[0]?.trim()?.slice(0, 50) || ''
      return { topic: t, children: desc ? [{ topic: desc }] : [] }
    }

    const buildCatNodes = (cats: Record<string, AnyItem[]>): MindMapNode[] =>
      Object.entries(cats).map(([cat, items]) => ({
        topic: isCase ? (caseTypeLabels[cat] || cat) : (categoryLabels[cat as keyof typeof categoryLabels] || cat),
        children: items.map(buildLeaf),
      }))

    if (hasGroups) {
      for (const [group, modules] of Object.entries(grouped)) {
        const groupNode: MindMapNode = { topic: group, children: [] }
        for (const [mod, cats] of Object.entries(modules)) {
          groupNode.children!.push({ topic: mod, children: buildCatNodes(cats) })
        }
        root.children!.push(groupNode)
      }
      if (Object.keys(ungrouped).length) {
        const otherNode: MindMapNode = { topic: '未分组', children: [] }
        for (const [mod, cats] of Object.entries(ungrouped)) {
          otherNode.children!.push({ topic: mod, children: buildCatNodes(cats) })
        }
        root.children!.push(otherNode)
      }
    } else {
      for (const [mod, cats] of Object.entries(ungrouped)) {
        root.children!.push({ topic: mod, children: buildCatNodes(cats) })
      }
    }
  }

  if (hasCases) {
    buildTree(props.cases as AnyItem[], true)
  } else {
    buildTree(props.testPoints as AnyItem[], false)
  }

  if (props.integrationTests.length) {
    root.children!.push({
      topic: '流程联动',
      children: props.integrationTests.map(t => ({
        topic: t.title,
        children: t.expected_results.map(r => ({ topic: r })),
      })),
    })
  }

  return root
})

function nodeToText(node: MindMapNode, depth = 0): string {
  let text = `${'\t'.repeat(depth)}${node.topic}\n`
  for (const child of node.children || []) {
    text += nodeToText(child, depth + 1)
  }
  return text
}

async function copyMindMap() {
  const text = nodeToText(coverageTree.value).trimEnd()
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

function convertToMindElixirData(node: MindMapNode, id = 'root', depth = 0): Record<string, unknown> {
  return {
    topic: node.topic,
    id,
    ...(id === 'root' ? { root: true } : {}),
    ...(depth === 1 ? { direction: parseInt(id.split('-')[1]) % 2 === 0 ? 0 : 1 } : {}),
    children: (node.children || []).map((child, i) =>
      convertToMindElixirData(child, `${id}-${i}`, depth + 1)
    ),
  }
}

function renderMindMap() {
  if (!containerRef.value) return
  if (meInstance) {
    meInstance.destroy()
    meInstance = null
  }

  const nodeData = convertToMindElixirData(coverageTree.value)

  meInstance = new MindElixir({
    el: containerRef.value,
    direction: MindElixir.SIDE,
    draggable: true,
    editable: false,
    contextMenu: false,
    toolBar: true,
    keypress: false,
  } as ConstructorParameters<typeof MindElixir>[0])

  meInstance.init({ nodeData } as unknown as Parameters<typeof meInstance.init>[0])
}

onMounted(() => nextTick(renderMindMap))

watch(
  () => [props.testPoints, props.integrationTests],
  () => nextTick(renderMindMap),
  { deep: true },
)

onBeforeUnmount(() => {
  if (meInstance) {
    meInstance.destroy()
    meInstance = null
  }
})
</script>

<template>
  <div class="mindmap-wrapper">
    <div v-if="!props.testPoints.length && !props.cases.length" class="mindmap-empty">
      暂无测试点或用例数据，无法生成脑图
    </div>
    <div v-else class="mindmap-content">
      <button class="mindmap-copy-btn" :class="{ copied }" @click="copyMindMap" :title="copied ? '已复制' : '复制为文本'">
        <svg v-if="!copied" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
        <svg v-else width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
        {{ copied ? '已复制' : '复制' }}
      </button>
      <div class="mindmap-container" ref="containerRef"></div>
    </div>
  </div>
</template>

<style scoped>
.mindmap-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text-faint, #94a3b8);
  font-size: 14px;
}
.mindmap-wrapper {
  width: 100%;
  min-height: 500px;
  position: relative;
}
.mindmap-container {
  width: 100%;
  height: 600px;
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 8px;
  overflow: hidden;
  background: #FAFBFC;
}
.mindmap-content {
  position: relative;
}
.mindmap-copy-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  background: rgba(255,255,255,0.92);
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  backdrop-filter: blur(4px);
  transition: all 0.15s ease;
}
.mindmap-copy-btn:hover {
  background: #EEF2FF;
  color: #4F46E5;
  border-color: #C7D2FE;
}
.mindmap-copy-btn.copied {
  background: #F0FDF4;
  color: #16A34A;
  border-color: #BBF7D0;
}
</style>
