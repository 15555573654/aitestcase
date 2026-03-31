from __future__ import annotations

from typing import Optional

from ..models import (
    AnalysisArtifact,
    ClarificationArtifact,
    ClarificationAnswer,
    ClarificationLLMOutput,
    RiskAcceptance,
)
from ..prompts import build_clarification_system_prompt, build_clarification_user_prompt
from .artifact_utils import build_meta, normalize_prefixed_id
from .llm import LLMService


class ClarificationService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def clarify(
        self,
        *,
        analysis: AnalysisArtifact,
        previous: Optional[ClarificationArtifact] = None,
        answers: Optional[list[ClarificationAnswer]] = None,
        risk_acceptance: Optional[RiskAcceptance] = None,
    ) -> tuple[ClarificationArtifact, dict[str, str]]:
        merged_answers = self._merge_answers(previous.answers if previous else [], answers or [])
        seed = previous.model_copy(deep=True) if previous else None
        if seed:
            seed.answers = merged_answers
        system_prompt = build_clarification_system_prompt()
        user_prompt = build_clarification_user_prompt(analysis, seed)
        raw_result = await self.llm_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=ClarificationLLMOutput.model_json_schema(),
            temperature=0.1,
        )
        llm_output = ClarificationLLMOutput.model_validate(raw_result)
        for idx, node in enumerate(llm_output.updated_requirement_nodes, start=1):
            prefix = node.id.split("-")[0] if node.id else "REQ"
            node.id = normalize_prefixed_id(node.id, prefix, idx)
        for idx, question in enumerate(llm_output.clarification_questions, start=1):
            question.id = normalize_prefixed_id(question.id, "CQ", idx)

        unresolved_blocking_ids = [item.id for item in llm_output.clarification_questions if item.blocking]
        artifact = ClarificationArtifact(
            meta=build_meta(
                artifact_type="clarification",
                workflow_run_id=analysis.meta.workflow_run_id,
                parent_ids=[analysis.meta.artifact_id],
            ),
            analysis_artifact_id=analysis.meta.artifact_id,
            resolved_summary=llm_output.resolved_summary,
            updated_requirement_nodes=llm_output.updated_requirement_nodes or analysis.requirement_nodes,
            clarification_questions=llm_output.clarification_questions,
            answers=merged_answers,
            unresolved_blocking_ids=unresolved_blocking_ids,
            round=(previous.round + 1) if previous else 1,
            risk_acceptance=risk_acceptance,
        )
        return artifact, {
            "clarification_system_prompt": system_prompt,
            "clarification_user_prompt": user_prompt,
        }

    def _merge_answers(
        self,
        existing: list[ClarificationAnswer],
        incoming: list[ClarificationAnswer],
    ) -> list[ClarificationAnswer]:
        merged: dict[str, ClarificationAnswer] = {item.question_id: item for item in existing}
        for item in incoming:
            merged[item.question_id] = item
        return list(merged.values())
