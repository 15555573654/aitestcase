export type Platform = 'web' | 'app' | 'plugin'
export type RiskLevel = 'high' | 'medium' | 'low'
export type Priority = 'P0' | 'P1' | 'P2'
export type TestCategory =
  | 'positive'
  | 'boundary'
  | 'exception'
  | 'permission'
  | 'state'
  | 'data_validation'
  | 'platform'
export type CaseType =
  | 'functional'
  | 'boundary'
  | 'exception'
  | 'permission'
  | 'platform'
  | 'integration'
export type HistoryStage = 'summary' | 'test_design' | 'case_suite'

export interface PlatformOption {
  label: string
  value: Platform
  description: string
}

export interface ProjectOption {
  label: string
  value: string
}

export interface MetaResponse {
  platforms: PlatformOption[]
  projects: ProjectOption[]
  workflow_steps: string[]
}

export interface ExperimentGroup {
  name: string
  description: string
  main_flow: string[]
  exception_flows: string[]
  business_rules: string[]
}

export interface StructuredSummary {
  title: string
  business_goal: string
  actors: string[]
  main_flow: string[]
  exception_flows: string[]
  business_rules: string[]
  experiment_groups: ExperimentGroup[]
}

export interface ClarificationQuestion {
  id: string
  question: string
  reason: string
  blocking: boolean
}

export interface ClarificationAnswer {
  question_id: string
  question: string
  answer: string
}

export interface ClarificationGap {
  field: string
  detail: string
  severity: RiskLevel
}

export interface TestPoint {
  id: string
  title: string
  function_module: string
  category: TestCategory
  description: string
  source: string
  risk_level: RiskLevel
  priority: Priority
  platform_specific: boolean
}

export interface ReviewNote {
  note_type: 'ADDED' | 'REMOVED' | 'MODIFIED' | 'WARNING'
  message: string
  severity: RiskLevel
  target_test_point_id: string
}

export interface ValidationIssue {
  issue_type: string
  message: string
  severity: RiskLevel
  target_type: string
  target_id: string
}

export interface TestCase {
  id: string
  title: string
  function_module: string
  case_type: CaseType
  priority: Priority
  requirement_refs: string[]
  summary_refs: string[]
  source_origin: string
  preconditions: string[]
  test_data: string[]
  steps: string[]
  expected_results: string[]
  coverage_tags: string[]
  platform: Platform
  source_test_point_id: string
}

export interface IntegrationTest {
  id: string
  title: string
  description: string
  flow: string
  preconditions: string[]
  steps: string[]
  expected_results: string[]
}

export interface RegressionSuite {
  id: string
  title: string
  description: string
  case_ids: string[]
  integration_test_ids: string[]
  entry_criteria: string[]
}

export interface ClarifyResponse {
  platform: Platform
  summary: StructuredSummary
  clarification_questions: ClarificationQuestion[]
  is_complete: boolean
  missing_fields: ClarificationGap[]
  resolved_fields: string[]
  remaining_risks: string[]
  round: number
  prompts: Record<string, string>
}

export interface AnalyzeStructureResponse {
  platform: Platform
  functions: string[]
  flows: string[]
  module_segments: Record<string, string>
  coverage_dimensions: string[]
  prompts: Record<string, string>
}

export interface GenerateTestPointsResponse {
  platform: Platform
  functions: string[]
  flows: string[]
  module_segments: Record<string, string>
  coverage_dimensions: string[]
  test_points: TestPoint[]
  prompts: Record<string, string>
}

export interface ReviewTestPointsResponse {
  platform: Platform
  reviewed_test_points: TestPoint[]
  review_notes: ReviewNote[]
  validation_issues: ValidationIssue[]
  prompts: Record<string, string>
}

export interface GenerateCasesResponse {
  platform: Platform
  cases: TestCase[]
  validation_issues: ValidationIssue[]
  prompts: Record<string, string>
}

export interface IntegrationTestsResponse {
  platform: Platform
  integration_tests: IntegrationTest[]
  validation_issues: ValidationIssue[]
  prompts: Record<string, string>
}

export interface TaskInputSnapshot {
  requirement_text: string
  source_type: string
  source_title: string
  source_url: string
  source_markdown: string
}

export interface TestDesignSnapshot {
  summary: StructuredSummary
  clarification_questions: ClarificationQuestion[]
  clarification_answers: ClarificationAnswer[]
  missing_fields: ClarificationGap[]
  resolved_fields: string[]
  remaining_risks: string[]
  functions: string[]
  flows: string[]
  module_segments: Record<string, string>
  coverage_dimensions: string[]
  test_points: TestPoint[]
  reviewed_test_points: TestPoint[]
  review_notes: ReviewNote[]
}

export interface CaseSuiteSnapshot {
  cases: TestCase[]
  integration_tests: IntegrationTest[]
  regression_suites: RegressionSuite[]
  validation_issues: ValidationIssue[]
}

export interface HistoryRecordData {
  task_input: TaskInputSnapshot
  test_design: TestDesignSnapshot
  case_suite?: CaseSuiteSnapshot | null
}

export interface HistoryRecord {
  id: string
  title: string
  platform: Platform
  project: string
  stage: HistoryStage
  cases_count: number
  integration_count: number
  timestamp: string
  data: HistoryRecordData
}

export interface TaskFormState {
  platform: Platform
  project: string
  requirementText: string
}

export const categoryLabels: Record<TestCategory, string> = {
  positive: '正向流程',
  boundary: '边界值',
  exception: '异常处理',
  permission: '权限控制',
  state: '状态流转',
  data_validation: '数据校验',
  platform: '平台专项',
}
