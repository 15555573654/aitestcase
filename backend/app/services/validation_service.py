from __future__ import annotations

from collections import Counter

from ..models import (
    AnalysisArtifact,
    ArtifactMeta,
    CaseBundleArtifact,
    CoverageDimension,
    CoverageSummary,
    ReviewedTestPointsArtifact,
    RiskLevel,
    TraceabilityLink,
    ValidationIssue,
    ValidationReport,
)
from .artifact_utils import build_meta


class ValidationService:
    REQUIRED_DIMENSIONS = {
        CoverageDimension.MAIN_FLOW.value,
        CoverageDimension.EXCEPTION.value,
        CoverageDimension.BOUNDARY.value,
        CoverageDimension.PERMISSION.value,
        CoverageDimension.STATE.value,
        CoverageDimension.PLATFORM.value,
    }

    def validate(
        self,
        *,
        workflow_run_id: str,
        analysis: AnalysisArtifact,
        reviewed_points: ReviewedTestPointsArtifact,
        case_bundle: CaseBundleArtifact,
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []
        traceability: list[TraceabilityLink] = []

        point_map = {item.id: item for item in reviewed_points.reviewed_test_points}
        case_titles = [item.title for item in case_bundle.cases]
        integration_titles = [item.title for item in case_bundle.integration_tests]

        duplicate_case_titles = [title for title, count in Counter(case_titles).items() if count > 1]
        duplicate_integration_titles = [title for title, count in Counter(integration_titles).items() if count > 1]

        for title in duplicate_case_titles:
            issues.append(
                ValidationIssue(
                    issue_type="duplicate_case_title",
                    message=f"存在重复功能用例标题：{title}",
                    severity=RiskLevel.MEDIUM,
                    related_ids=[title],
                )
            )

        for title in duplicate_integration_titles:
            issues.append(
                ValidationIssue(
                    issue_type="duplicate_integration_title",
                    message=f"存在重复流程联动标题：{title}",
                    severity=RiskLevel.MEDIUM,
                    related_ids=[title],
                )
            )

        selected_ids = set(case_bundle.selected_test_point_ids)
        covered_ids = {item.source_test_point_id for item in case_bundle.cases}
        missing_ids = sorted(selected_ids - covered_ids)
        for missing_id in missing_ids:
            issues.append(
                ValidationIssue(
                    issue_type="coverage_gap",
                    message=f"测试点 {missing_id} 没有生成功能用例。",
                    severity=RiskLevel.HIGH,
                    related_ids=[missing_id],
                )
            )

        for case in case_bundle.cases:
            point = point_map.get(case.source_test_point_id)
            if not point:
                issues.append(
                    ValidationIssue(
                        issue_type="traceability",
                        message=f"{case.id} 的 source_test_point_id 无法匹配 reviewed_test_points。",
                        severity=RiskLevel.HIGH,
                        related_ids=[case.id, case.source_test_point_id],
                    )
                )
                continue
            if len(case.steps) < 2:
                issues.append(
                    ValidationIssue(
                        issue_type="executability",
                        message=f"{case.id} 的测试步骤不足 2 步。",
                        severity=RiskLevel.HIGH,
                        related_ids=[case.id],
                    )
                )
            if len(case.expected_results) < 2:
                issues.append(
                    ValidationIssue(
                        issue_type="assertability",
                        message=f"{case.id} 的预期结果不足 2 条。",
                        severity=RiskLevel.HIGH,
                        related_ids=[case.id],
                    )
                )
            if not case.requirement_ids:
                issues.append(
                    ValidationIssue(
                        issue_type="traceability",
                        message=f"{case.id} 缺少 requirement_ids。",
                        severity=RiskLevel.HIGH,
                        related_ids=[case.id],
                    )
                )
            for requirement_id in case.requirement_ids:
                traceability.append(
                    TraceabilityLink(
                        requirement_id=requirement_id,
                        test_point_id=point.id,
                        case_id=case.id,
                    )
                )

        case_title_set = {title.strip() for title in case_titles}
        for integration in case_bundle.integration_tests:
            if len(integration.steps) < 2 or len(integration.expected_results) < 2:
                issues.append(
                    ValidationIssue(
                        issue_type="integration_executability",
                        message=f"{integration.id} 的流程联动场景不完整。",
                        severity=RiskLevel.HIGH,
                        related_ids=[integration.id],
                    )
                )
            if not integration.flow_id:
                issues.append(
                    ValidationIssue(
                        issue_type="traceability",
                        message=f"{integration.id} 缺少 flow_id。",
                        severity=RiskLevel.MEDIUM,
                        related_ids=[integration.id],
                    )
                )
            if integration.title.strip() in case_title_set:
                issues.append(
                    ValidationIssue(
                        issue_type="duplicate_cross_layer",
                        message=f"{integration.id} 与功能用例标题重复：{integration.title}",
                        severity=RiskLevel.MEDIUM,
                        related_ids=[integration.id, integration.title],
                    )
                )
            for requirement_id in integration.requirement_ids:
                traceability.append(
                    TraceabilityLink(
                        requirement_id=requirement_id,
                        integration_test_id=integration.id,
                    )
                )

        invalid_review_refs = [
            note.target_test_point_id
            for note in reviewed_points.review_notes
            if note.target_test_point_id and note.target_test_point_id not in point_map
        ]
        for invalid_id in invalid_review_refs:
            issues.append(
                ValidationIssue(
                    issue_type="review_reference",
                    message=f"review note 指向不存在的测试点：{invalid_id}",
                    severity=RiskLevel.HIGH,
                    related_ids=[invalid_id],
                )
            )

        covered_dimensions = sorted({item.category.value for item in reviewed_points.reviewed_test_points})
        missing_dimensions = sorted(self.REQUIRED_DIMENSIONS - set(covered_dimensions))
        for dimension in missing_dimensions:
            issues.append(
                ValidationIssue(
                    issue_type="dimension_gap",
                    message=f"缺少关键覆盖维度：{dimension}",
                    severity=RiskLevel.MEDIUM,
                    related_ids=[dimension],
                )
            )

        for requirement in analysis.requirement_nodes:
            linked = any(link.requirement_id == requirement.id for link in traceability)
            if not linked and requirement.node_type.value in {"requirement", "rule", "flow"}:
                issues.append(
                    ValidationIssue(
                        issue_type="untraced_requirement",
                        message=f"需求节点 {requirement.id} 未形成下游追溯链。",
                        severity=RiskLevel.MEDIUM,
                        related_ids=[requirement.id],
                    )
                )

        coverage_summary = CoverageSummary(
            total_test_points=len(reviewed_points.reviewed_test_points),
            total_selected_points=len(case_bundle.selected_test_point_ids),
            total_cases=len(case_bundle.cases),
            total_integration_tests=len(case_bundle.integration_tests),
            covered_dimensions=covered_dimensions,
            missing_dimensions=missing_dimensions,
            uncovered_test_point_ids=missing_ids,
            duplicate_titles=duplicate_case_titles + duplicate_integration_titles,
        )
        meta: ArtifactMeta = build_meta(
            artifact_type="validation-report",
            workflow_run_id=workflow_run_id,
            parent_ids=[case_bundle.meta.artifact_id],
        )
        return ValidationReport(
            meta=meta,
            case_bundle_artifact_id=case_bundle.meta.artifact_id,
            issues=issues,
            traceability=traceability,
            coverage_summary=coverage_summary,
        )
