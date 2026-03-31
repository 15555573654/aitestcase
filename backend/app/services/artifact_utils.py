from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..models import ArtifactMeta, PlatformType, SCHEMA_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_meta(
    artifact_type: str,
    workflow_run_id: str,
    parent_ids: Optional[list[str]] = None,
) -> ArtifactMeta:
    prefix = artifact_type.upper().replace("-", "_")
    return ArtifactMeta(
        artifact_id=f"{prefix}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        artifact_type=artifact_type,
        workflow_run_id=workflow_run_id,
        schema_version=SCHEMA_VERSION,
        parent_ids=parent_ids or [],
        created_at=utc_now_iso(),
    )


def build_run_id(platform: PlatformType) -> str:
    return f"run-{platform.value}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"


def normalize_prefixed_id(value: Optional[str], prefix: str, index: int) -> str:
    if value:
        clean = value.strip().upper()
        if clean.startswith(f"{prefix}-") and clean.split("-")[-1].isdigit():
            return f"{prefix}-{int(clean.split('-')[-1]):03d}"
    return f"{prefix}-{index:03d}"
