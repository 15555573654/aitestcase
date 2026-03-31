import type {
  AnalyzeStructureResponse,
  ClarificationAnswer,
  ClarificationQuestion,
  ClarifyResponse,
  GenerateCasesResponse,
  GenerateTestPointsResponse,
  HistoryRecord,
  IntegrationTestsResponse,
  ReviewTestPointsResponse,
  StructuredSummary,
  TestPoint,
} from './types'
import type { Platform, TaskFormState } from './types'
import { requestJson, splitLines } from '../../core/api'

export { splitLines }

export const createWorkflowApi = (baseUrl: string) => ({

  async uploadPdf(file: File): Promise<{ text: string; pages: number }> {
    const formData = new FormData()
    formData.append('file', file)
    return requestJson<{ text: string; pages: number }>(
      `${baseUrl}/api/upload-pdf`,
      { method: 'POST', body: formData },
      'PDF 解析失败',
    )
  },

  async clarify(form: TaskFormState, clarificationAnswers: ClarificationAnswer[], images?: string[], currentSummary?: StructuredSummary): Promise<ClarifyResponse> {
    return requestJson<ClarifyResponse>(
      `${baseUrl}/api/workflow/clarify`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: form.platform,
          project: form.project,
          requirement_text: form.requirementText,
          clarification_answers: clarificationAnswers,
          images: images || [],
          current_summary: currentSummary || null,
        }),
      },
      '需求解析失败',
    )
  },

  async analyzeStructure(
    platform: Platform,
    summary: StructuredSummary,
    clarificationAnswers: ClarificationAnswer[],
    clarificationQuestions: ClarificationQuestion[],
  ): Promise<AnalyzeStructureResponse> {
    return requestJson<AnalyzeStructureResponse>(
      `${baseUrl}/api/workflow/analyze-structure`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          summary,
          clarification_answers: clarificationAnswers,
          clarification_questions: clarificationQuestions,
        }),
      },
      '结构分析失败',
    )
  },

  async generateTestPoints(
    platform: Platform,
    summary: StructuredSummary,
    functions: string[],
    flows: string[],
    moduleSegments: Record<string, string>,
    coverageDimensions: string[],
    clarificationAnswers: ClarificationAnswer[],
  ): Promise<GenerateTestPointsResponse> {
    return requestJson<GenerateTestPointsResponse>(
      `${baseUrl}/api/workflow/generate-test-points`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          summary,
          functions,
          flows,
          module_segments: moduleSegments,
          coverage_dimensions: coverageDimensions,
          clarification_answers: clarificationAnswers,
        }),
      },
      '测试点生成失败',
    )
  },

  async reviewTestPoints(
    platform: Platform,
    summary: StructuredSummary,
    clarificationAnswers: ClarificationAnswer[],
    testPoints: TestPoint[],
  ): Promise<ReviewTestPointsResponse> {
    return requestJson<ReviewTestPointsResponse>(
      `${baseUrl}/api/workflow/review-test-points`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          summary,
          clarification_answers: clarificationAnswers,
          test_points: testPoints,
        }),
      },
      '测试点审核失败',
    )
  },

  async generateCaseSuite(
    platform: Platform,
    summary: StructuredSummary,
    functions: string[],
    flows: string[],
    moduleSegments: Record<string, string>,
    selectedTestPoints: TestPoint[],
  ): Promise<GenerateCasesResponse> {
    return requestJson<GenerateCasesResponse>(
      `${baseUrl}/api/workflow/generate-cases`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          summary,
          functions,
          flows,
          module_segments: moduleSegments,
          selected_test_points: selectedTestPoints,
        }),
      },
      '测试用例生成失败',
    )
  },

  async generateIntegrationTests(
    platform: Platform,
    summary: StructuredSummary,
    flows: string[],
    testPoints: TestPoint[],
    caseTitles: string[],
  ): Promise<IntegrationTestsResponse> {
    return requestJson<IntegrationTestsResponse>(
      `${baseUrl}/api/workflow/integration-tests`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          summary,
          flows,
          reviewed_test_points: testPoints,
          functional_case_titles: caseTitles,
        }),
      },
      '联动测试生成失败',
    )
  },

  async listHistory(): Promise<HistoryRecord[]> {
    return requestJson<HistoryRecord[]>(`${baseUrl}/api/history`, { method: 'GET' }, '获取历史记录失败')
  },

  async saveHistory(record: HistoryRecord): Promise<HistoryRecord> {
    return requestJson<HistoryRecord>(
      `${baseUrl}/api/history`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(record),
      },
      '保存历史记录失败',
    )
  },

  async deleteHistory(id: string): Promise<void> {
    await requestJson<{ status: string }>(
      `${baseUrl}/api/history/${id}`,
      { method: 'DELETE' },
      '删除历史记录失败',
    )
  },

  // ── 飞书文档 ──

  async feishuFetchDoc(
    docUrl: string,
  ): Promise<{ title: string; markdown: string; images: { index: number; data_url: string; context: string }[]; images_count: number; source_type: string }> {
    return requestJson(`${baseUrl}/api/feishu/fetch-doc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_url: docUrl }),
    }, '飞书文档获取失败')
  },

  // ── 项目知识库 ──

  async getKnowledge(project: string): Promise<{ project: string; content: string }> {
    return requestJson(`${baseUrl}/api/knowledge/${encodeURIComponent(project)}`, { method: 'GET' }, '获取知识库失败')
  },

  async saveKnowledge(project: string, content: string): Promise<{ status: string }> {
    return requestJson(`${baseUrl}/api/knowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project, content }),
    }, '保存知识库失败')
  },

  async generateKnowledgeDraft(params: {
    project: string; requirement_text?: string; summary_title?: string
    business_rules?: string[]; test_points_summary?: string
  }): Promise<{ draft: string; existing: string }> {
    return requestJson(`${baseUrl}/api/knowledge/generate-draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }, '生成知识库草稿失败')
  },
})
