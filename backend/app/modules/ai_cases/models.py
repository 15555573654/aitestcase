from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    WEB = "web"
    APP = "app"
    PLUGIN = "plugin"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseType(str, Enum):
    FUNCTIONAL = "functional"
    BOUNDARY = "boundary"
    EXCEPTION = "exception"
    PERMISSION = "permission"
    PLATFORM = "platform"
    INTEGRATION = "integration"


class NoteType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    WARNING = "WARNING"


class TestCategory(str, Enum):
    POSITIVE = "positive"
    BOUNDARY = "boundary"
    EXCEPTION = "exception"
    PERMISSION = "permission"
    STATE = "state"
    DATA_VALIDATION = "data_validation"
    PLATFORM = "platform"


class HistoryStage(str, Enum):
    SUMMARY = "summary"
    TEST_DESIGN = "test_design"
    CASE_SUITE = "case_suite"


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    reason: str
    blocking: bool = True


class ClarificationAnswer(BaseModel):
    question_id: str
    question: str
    answer: str


class ClarificationGap(BaseModel):
    field: str
    detail: str
    severity: RiskLevel = RiskLevel.MEDIUM


class ExperimentGroup(BaseModel):
    """AB 测试/灰度实验分组。"""
    name: str = ""
    description: str = ""
    main_flow: list[str] = Field(default_factory=list)
    exception_flows: list[str] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)


class StructuredSummary(BaseModel):
    title: str = ""
    business_goal: str = ""
    actors: list[str] = Field(default_factory=list)
    main_flow: list[str] = Field(default_factory=list)
    exception_flows: list[str] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    experiment_groups: list[ExperimentGroup] = Field(default_factory=list)


class TestPoint(BaseModel):
    id: str = ""
    title: str
    function_module: str = ""
    category: TestCategory = TestCategory.POSITIVE
    description: str
    source: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    priority: Priority = Priority.P1
    platform_specific: bool = False


class ValidationIssue(BaseModel):
    issue_type: str
    message: str
    severity: RiskLevel = RiskLevel.MEDIUM
    target_type: str = "global"
    target_id: str = ""


class ReviewNote(BaseModel):
    note_type: NoteType
    message: str
    severity: RiskLevel = RiskLevel.MEDIUM
    target_test_point_id: str = ""


class TestCase(BaseModel):
    id: str = ""
    title: str
    function_module: str = ""
    case_type: CaseType = CaseType.FUNCTIONAL
    priority: Priority = Priority.P1
    requirement_refs: list[str] = Field(default_factory=list)
    summary_refs: list[str] = Field(default_factory=list)
    source_origin: str = ""
    preconditions: list[str] = Field(default_factory=list)
    test_data: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_results: list[str] = Field(default_factory=list)
    coverage_tags: list[str] = Field(default_factory=list)
    platform: PlatformType
    source_test_point_id: str


class IntegrationTest(BaseModel):
    id: str = ""
    title: str
    description: str
    flow: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_results: list[str] = Field(default_factory=list)


class RegressionSuite(BaseModel):
    id: str
    title: str
    description: str
    case_ids: list[str] = Field(default_factory=list)
    integration_test_ids: list[str] = Field(default_factory=list)
    entry_criteria: list[str] = Field(default_factory=list)


class ClarifyRequest(BaseModel):
    platform: PlatformType
    project: str = ""
    requirement_text: str = Field(min_length=10)
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list, description="base64 data URL 图片列表")
    current_summary: Optional[StructuredSummary] = Field(default=None, description="当前已编辑的摘要（整合调用时传入）")


class ClarifyResponse(BaseModel):
    platform: PlatformType
    summary: StructuredSummary
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    is_complete: bool = False
    missing_fields: list[ClarificationGap] = Field(default_factory=list)
    resolved_fields: list[str] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    round: int = 1
    prompts: dict[str, str] = Field(default_factory=dict)


class ClarifyLLMOutput(BaseModel):
    summary: StructuredSummary
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    is_complete: bool = False


class AnalyzeStructureRequest(BaseModel):
    platform: PlatformType
    summary: StructuredSummary
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)


class AnalyzeStructureResponse(BaseModel):
    platform: PlatformType
    functions: list[str] = Field(default_factory=list)
    flows: list[str] = Field(default_factory=list)
    module_segments: dict[str, str] = Field(default_factory=dict)
    coverage_dimensions: list[str] = Field(default_factory=list)
    prompts: dict[str, str] = Field(default_factory=dict)


class AnalyzeStructureLLMOutput(BaseModel):
    functions: list[str] = Field(default_factory=list)
    flows: list[str] = Field(default_factory=list)
    module_segments: dict[str, str] = Field(default_factory=dict)
    coverage_dimensions: list[str] = Field(default_factory=list)


class GenerateTestPointsRequest(BaseModel):
    platform: PlatformType
    summary: StructuredSummary
    functions: list[str] = Field(default_factory=list)
    flows: list[str] = Field(default_factory=list)
    module_segments: dict[str, str] = Field(default_factory=dict)
    coverage_dimensions: list[str] = Field(default_factory=list)
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list)


class GenerateTestPointsResponse(BaseModel):
    platform: PlatformType
    functions: list[str] = Field(default_factory=list)
    flows: list[str] = Field(default_factory=list)
    module_segments: dict[str, str] = Field(default_factory=dict)
    coverage_dimensions: list[str] = Field(default_factory=list)
    test_points: list[TestPoint] = Field(default_factory=list)
    prompts: dict[str, str] = Field(default_factory=dict)


class GenerateTestPointsLLMOutput(BaseModel):
    test_points: list[TestPoint] = Field(default_factory=list)


class ReviewTestPointsRequest(BaseModel):
    platform: PlatformType
    summary: StructuredSummary
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list)
    test_points: list[TestPoint] = Field(default_factory=list)


class ReviewTestPointsResponse(BaseModel):
    platform: PlatformType
    reviewed_test_points: list[TestPoint] = Field(default_factory=list)
    review_notes: list[ReviewNote] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    prompts: dict[str, str] = Field(default_factory=dict)


class ReviewTestPointsLLMOutput(BaseModel):
    reviewed_test_points: list[TestPoint] = Field(default_factory=list)
    review_notes: list[ReviewNote] = Field(default_factory=list)


class GenerateCasesRequest(BaseModel):
    platform: PlatformType
    summary: StructuredSummary
    functions: list[str] = Field(default_factory=list)
    flows: list[str] = Field(default_factory=list)
    module_segments: dict[str, str] = Field(default_factory=dict)
    selected_test_points: list[TestPoint] = Field(default_factory=list)


class GenerateCasesResponse(BaseModel):
    platform: PlatformType
    cases: list[TestCase] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    prompts: dict[str, str] = Field(default_factory=dict)


class GenerateCasesLLMOutput(BaseModel):
    cases: list[TestCase] = Field(default_factory=list)


class IntegrationTestsRequest(BaseModel):
    platform: PlatformType
    summary: StructuredSummary
    flows: list[str] = Field(default_factory=list)
    reviewed_test_points: list[TestPoint] = Field(default_factory=list)
    functional_case_titles: list[str] = Field(default_factory=list)


class IntegrationTestsResponse(BaseModel):
    platform: PlatformType
    integration_tests: list[IntegrationTest] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    prompts: dict[str, str] = Field(default_factory=dict)


class IntegrationTestsLLMOutput(BaseModel):
    integration_tests: list[IntegrationTest] = Field(default_factory=list)



class PlatformOption(BaseModel):
    label: str
    value: PlatformType
    description: str


class ProjectOption(BaseModel):
    label: str
    value: str


class MetaResponse(BaseModel):
    platforms: list[PlatformOption]
    projects: list[ProjectOption] = Field(default_factory=list)
    workflow_steps: list[str]


class TaskInputSnapshot(BaseModel):
    requirement_text: str = ""
    source_type: str = ""
    source_title: str = ""
    source_url: str = ""
    source_markdown: str = ""


class TestDesignSnapshot(BaseModel):
    summary: StructuredSummary
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list)
    missing_fields: list[ClarificationGap] = Field(default_factory=list)
    resolved_fields: list[str] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    functions: list[str] = Field(default_factory=list)
    flows: list[str] = Field(default_factory=list)
    module_segments: dict[str, str] = Field(default_factory=dict)
    coverage_dimensions: list[str] = Field(default_factory=list)
    test_points: list[TestPoint] = Field(default_factory=list)
    reviewed_test_points: list[TestPoint] = Field(default_factory=list)
    review_notes: list[ReviewNote] = Field(default_factory=list)


class CaseSuiteSnapshot(BaseModel):
    cases: list[TestCase] = Field(default_factory=list)
    integration_tests: list[IntegrationTest] = Field(default_factory=list)
    regression_suites: list[RegressionSuite] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)


class HistoryRecordData(BaseModel):
    task_input: TaskInputSnapshot
    test_design: TestDesignSnapshot
    case_suite: Optional[CaseSuiteSnapshot] = None


class HistoryRecord(BaseModel):
    id: str
    title: str
    platform: PlatformType
    project: str = ""
    stage: HistoryStage = HistoryStage.SUMMARY
    cases_count: int = 0
    integration_count: int = 0
    timestamp: str
    data: HistoryRecordData
