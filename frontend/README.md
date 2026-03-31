# Frontend

前端基于 Vue 3 + TypeScript + Vite，当前已经重构为组件化工作流容器。

## 核心组件

- `src/components/RequirementInputStep.vue`
- `src/components/SummaryConfirmStep.vue`
- `src/components/TestDesignStep.vue`
- `src/components/CaseSuiteStep.vue`
- `src/components/HistorySidebar.vue`
- `src/components/MindMapView.vue`

## 当前职责

- 需求输入与 PDF 导入
- 澄清问题回答与摘要确认
- 测试点人工筛选与 AI 评审
- 功能用例、联动测试、回归集展示
- 历史任务读取与恢复

## 类型约束

前端与后端契约统一使用：

- `src/types/workflow.ts`

不要再在页面组件里手写独立的接口类型定义。
