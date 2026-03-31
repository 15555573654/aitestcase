from __future__ import annotations

from ..models import (
    AnalysisArtifact,
    CaseBundleArtifact,
    ClarificationArtifact,
    FinalWorkflowBundle,
    GenerateCasesLLMOutput,
    IntegrationTestsLLMOutput,
    PlatformType,
    ReviewedTestPointsArtifact,
    TestPoint,
    ValidationReport,
)
from ..prompts import (
    build_cases_system_prompt,
    build_cases_user_prompt,
    build_integration_system_prompt,
    build_integration_user_prompt,
)
from .artifact_utils import build_meta, normalize_prefixed_id
from .llm import LLMService


class CaseGenerationService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def generate(
        self,
        *,
        analysis: AnalysisArtifact,
        reviewed: ReviewedTestPointsArtifact,
        selected_points: list[TestPoint],
        platform: PlatformType,
    ) -> tuple[CaseBundleArtifact, dict[str, str]]:
        system_prompt = build_cases_system_prompt()
        user_prompt = build_cases_user_prompt(analysis, reviewed, selected_points)
        raw_result = await self.llm_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=GenerateCasesLLMOutput.model_json_schema(),
            temperature=0.2,
        )
        llm_output = GenerateCasesLLMOutput.model_validate(raw_result)
        for idx, case in enumerate(llm_output.cases, start=1):
            case.id = normalize_prefixed_id(case.id, "TC", idx)
            case.platform = platform
        artifact = CaseBundleArtifact(
            meta=build_meta(
                artifact_type="case-bundle",
                workflow_run_id=analysis.meta.workflow_run_id,
                parent_ids=[reviewed.meta.artifact_id],
            ),
            reviewed_test_points_artifact_id=reviewed.meta.artifact_id,
            selected_test_point_ids=[item.id for item in selected_points],
            cases=llm_output.cases,
            integration_tests=[],
        )
        return artifact, {
            "case_system_prompt": system_prompt,
            "case_user_prompt": user_prompt,
        }


class IntegrationGenerationService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def generate(
        self,
        *,
        analysis: AnalysisArtifact,
        reviewed: ReviewedTestPointsArtifact,
        case_bundle: CaseBundleArtifact,
    ) -> tuple[CaseBundleArtifact, dict[str, str]]:
        system_prompt = build_integration_system_prompt()
        user_prompt = build_integration_user_prompt(analysis, reviewed, case_bundle)
        raw_result = await self.llm_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=IntegrationTestsLLMOutput.model_json_schema(),
            temperature=0.2,
        )
        llm_output = IntegrationTestsLLMOutput.model_validate(raw_result)
        for idx, item in enumerate(llm_output.integration_tests, start=1):
            item.id = normalize_prefixed_id(item.id, "IT", idx)
        updated = case_bundle.model_copy(deep=True)
        updated.integration_tests = llm_output.integration_tests
        return updated, {
            "integration_system_prompt": system_prompt,
            "integration_user_prompt": user_prompt,
        }


class FinalizationService:
    def build_final_bundle(
        self,
        *,
        raw_context,
        analysis: AnalysisArtifact,
        clarification: ClarificationArtifact,
        coverage_plan,
        reviewed_points: ReviewedTestPointsArtifact,
        case_bundle: CaseBundleArtifact,
        validation_report: ValidationReport,
    ) -> FinalWorkflowBundle:
        return FinalWorkflowBundle(
            meta=build_meta(
                artifact_type="final-bundle",
                workflow_run_id=analysis.meta.workflow_run_id,
                parent_ids=[validation_report.meta.artifact_id],
            ),
            raw_context=raw_context,
            analysis=analysis,
            clarification=clarification,
            coverage_plan=coverage_plan,
            reviewed_points=reviewed_points,
            case_bundle=case_bundle,
            validation_report=validation_report,
        )
