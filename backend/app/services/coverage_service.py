from __future__ import annotations

from ..models import AnalysisArtifact, ClarificationArtifact, CoveragePlanArtifact, CoveragePlanLLMOutput
from ..prompts import build_coverage_system_prompt, build_coverage_user_prompt
from .artifact_utils import build_meta, normalize_prefixed_id
from .llm import LLMService


class CoveragePlanningService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def build_plan(
        self,
        *,
        analysis: AnalysisArtifact,
        clarification: ClarificationArtifact,
    ) -> tuple[CoveragePlanArtifact, dict[str, str]]:
        system_prompt = build_coverage_system_prompt()
        user_prompt = build_coverage_user_prompt(analysis, clarification)
        raw_result = await self.llm_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=CoveragePlanLLMOutput.model_json_schema(),
            temperature=0.2,
        )
        llm_output = CoveragePlanLLMOutput.model_validate(raw_result)
        for idx, item in enumerate(llm_output.test_points, start=1):
            item.id = normalize_prefixed_id(item.id, "TP", idx)
        artifact = CoveragePlanArtifact(
            meta=build_meta(
                artifact_type="coverage-plan",
                workflow_run_id=analysis.meta.workflow_run_id,
                parent_ids=[analysis.meta.artifact_id, clarification.meta.artifact_id],
            ),
            analysis_artifact_id=analysis.meta.artifact_id,
            clarification_artifact_id=clarification.meta.artifact_id,
            coverage_dimensions=llm_output.coverage_dimensions,
            functions=analysis.functions,
            flows=analysis.flows,
            module_segments=analysis.module_segments,
            test_points=llm_output.test_points,
        )
        return artifact, {
            "coverage_system_prompt": system_prompt,
            "coverage_user_prompt": user_prompt,
        }
