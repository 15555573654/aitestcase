from __future__ import annotations

from ..models import (
    AnalysisArtifact,
    AnalysisLLMOutput,
    RawContextArtifact,
    RequirementNodeType,
)
from ..prompts import build_analysis_system_prompt, build_analysis_user_prompt
from .artifact_utils import build_meta, normalize_prefixed_id
from .llm import LLMService


class AnalysisService:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def analyze(self, raw_context: RawContextArtifact) -> tuple[AnalysisArtifact, dict[str, str]]:
        system_prompt = build_analysis_system_prompt()
        user_prompt = build_analysis_user_prompt(raw_context)
        raw_result = await self.llm_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=AnalysisLLMOutput.model_json_schema(),
            temperature=0.1,
        )
        llm_output = AnalysisLLMOutput.model_validate(raw_result)
        self._normalize_output(llm_output)
        artifact = AnalysisArtifact(
            meta=build_meta(
                artifact_type="analysis",
                workflow_run_id=raw_context.meta.workflow_run_id,
                parent_ids=[raw_context.meta.artifact_id],
            ),
            raw_context_artifact_id=raw_context.meta.artifact_id,
            summary=llm_output.summary,
            requirement_nodes=llm_output.requirement_nodes,
            functions=llm_output.functions,
            flows=llm_output.flows,
            module_segments=llm_output.module_segments,
            state_model=llm_output.state_model,
            role_permission_matrix=llm_output.role_permission_matrix,
            missing_information=llm_output.missing_information,
        )
        return artifact, {
            "analysis_system_prompt": system_prompt,
            "analysis_user_prompt": user_prompt,
        }

    def _normalize_output(self, output: AnalysisLLMOutput) -> None:
        node_prefix_map = {
            RequirementNodeType.REQUIREMENT: "REQ",
            RequirementNodeType.RULE: "RULE",
            RequirementNodeType.FLOW: "FLOW",
            RequirementNodeType.STATE: "STATE",
            RequirementNodeType.ROLE: "ROLE",
            RequirementNodeType.PLATFORM: "PF",
        }
        for idx, node in enumerate(output.requirement_nodes, start=1):
            prefix = node_prefix_map.get(node.node_type, "REQ")
            node.id = normalize_prefixed_id(node.id, prefix, idx)

        for idx, flow in enumerate(output.flows, start=1):
            flow.id = normalize_prefixed_id(flow.id, "FLOW", idx)
            if not flow.title:
                flow.title = f"业务流{idx}"

        for idx, segment in enumerate(output.module_segments, start=1):
            segment.id = normalize_prefixed_id(segment.id, "MOD", idx)
            if not segment.name:
                segment.name = f"模块{idx}"

        for idx, transition in enumerate(output.state_model.transitions, start=1):
            transition.id = normalize_prefixed_id(transition.id, "TRANS", idx)

        for idx, entry in enumerate(output.role_permission_matrix.entries, start=1):
            entry.id = normalize_prefixed_id(entry.id, "PERM", idx)
