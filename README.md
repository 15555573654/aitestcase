# AI TEST

一个面向 AI 测试设计场景的前后端项目，当前聚焦于：

- 需求澄清
- 摘要确认
- 测试点生成与评审
- 功能用例、联动测试、回归集生成
- 思维导图生成
- 历史任务资产沉淀

## 当前工作流

1. 需求输入
2. AI 澄清
3. 摘要确认
4. 测试设计
5. 用例与回归资产生成

本轮已完成的关键整改：

- `blocking` 澄清问题已在前后端都生效，未回答时不能进入测试点生成
- 澄清输出新增 `missing_fields`、`resolved_fields`、`remaining_risks`
- 用例生成改为按模块分批，再统一聚合与校验
- `generate-cases` 统一返回 `cases + integration_tests + regression_suites + validation_issues`
- 前端主流程已经组件化，不再依赖单个巨型 `App.vue` 页面承载全部逻辑
- 历史记录统一为任务资产结构，并兼容旧版本快照

## 目录结构

```text
backend/
  app/
    main.py
    models.py
    prompts.py
    services/
      workflow_service.py
      history_service.py
frontend/
  src/
    App.vue
    components/
    types/workflow.ts
```

## 后端接口

- `GET /health`
- `GET /api/meta`
- `POST /api/upload-pdf`
- `POST /api/workflow/clarify`
- `POST /api/workflow/generate-test-points`
- `POST /api/workflow/review-test-points`
- `POST /api/workflow/generate-cases`
- `POST /api/workflow/integration-tests`
- `POST /api/workflow/mindmap`
- `GET /api/history`
- `POST /api/history`
- `GET /api/history/{record_id}`
- `DELETE /api/history/{record_id}`

## 前端说明

前端当前采用组件化工作流：

- `RequirementInputStep.vue`
- `SummaryConfirmStep.vue`
- `TestDesignStep.vue`
- `CaseSuiteStep.vue`
- `HistorySidebar.vue`

所有核心类型统一收口到 `frontend/src/types/workflow.ts`。