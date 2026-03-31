from __future__ import annotations

from ..models import (
    AnalysisArtifact,
    ClarificationArtifact,
    CoveragePlanArtifact,
    ReviewedTestPointsArtifact,
    ReviewTestPointsLLMOutput,
)
from ..prompts import build_review_system_prompt, build_review_user_prompt
from .artifact_utils import build_meta, normalize_prefixed_id
from .llm import LLMService


class ReviewService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def review(
        self,
        *,
        analysis: AnalysisArtifact,
        clarification: ClarificationArtifact,
        coverage: CoveragePlanArtifact,
    ) -> tuple[ReviewedTestPointsArtifact, dict[str, str]]:
        system_prompt = build_review_system_prompt()
        user_prompt = build_review_user_prompt(analysis, clarification, coverage)
        raw_result = await self.llm_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=ReviewTestPointsLLMOutput.model_json_schema(),
            temperature=0.1,
        )
        llm_output = ReviewTestPointsLLMOutput.model_validate(raw_result)
        for idx, item in enumerate(llm_output.reviewed_test_points, start=1):
            item.id = normalize_prefixed_id(item.id, "TP", idx)
        valid_ids = {item.id for item in llm_output.reviewed_test_points}
        for note in llm_output.review_notes:
            if note.target_test_point_id and note.target_test_point_id not in valid_ids:
                note.target_test_point_id = ""
        artifact = ReviewedTestPointsArtifact(
            meta=build_meta(
                artifact_type="reviewed-test-points",
                workflow_run_id=analysis.meta.workflow_run_id,
                parent_ids=[coverage.meta.artifact_id],
            ),
            coverage_plan_artifact_id=coverage.meta.artifact_id,
            reviewed_test_points=llm_output.reviewed_test_points,
            review_notes=llm_output.review_notes,
        )
        return artifact, {
            "review_system_prompt": system_prompt,
            "review_user_prompt": user_prompt,
        }
