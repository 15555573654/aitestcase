from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..models import (
    AnalysisArtifact,
    ClarificationArtifact,
    CoveragePlanArtifact,
    FinalWorkflowBundle,
    RawContextArtifact,
    ReviewedTestPointsArtifact,
    WorkflowRunSnapshot,
    WorkflowStage,
)


@dataclass
class WorkflowRunState:
    run_id: str
    stage: WorkflowStage = WorkflowStage.INPUT
    raw_context: Optional[RawContextArtifact] = None
    analysis: Optional[AnalysisArtifact] = None
    clarification: Optional[ClarificationArtifact] = None
    coverage_plan: Optional[CoveragePlanArtifact] = None
    reviewed_points: Optional[ReviewedTestPointsArtifact] = None
    final_bundle: Optional[FinalWorkflowBundle] = None

    def to_snapshot(self) -> WorkflowRunSnapshot:
        return WorkflowRunSnapshot(
            run_id=self.run_id,
            stage=self.stage,
            raw_context=self.raw_context,
            analysis=self.analysis,
            clarification=self.clarification,
            coverage_plan=self.coverage_plan,
            reviewed_points=self.reviewed_points,
            final_bundle=self.final_bundle,
        )


class WorkflowStateService:
    def __init__(self) -> None:
        self._runs: dict[str, WorkflowRunState] = {}

    def create_run(self, run_id: str) -> WorkflowRunState:
        state = WorkflowRunState(run_id=run_id)
        self._runs[run_id] = state
        return state

    def get_run(self, run_id: str) -> Optional[WorkflowRunState]:
        return self._runs.get(run_id)

    def require_run(self, run_id: str) -> WorkflowRunState:
        state = self.get_run(run_id)
        if not state:
            raise ValueError(f"workflow run 不存在: {run_id}")
        return state
