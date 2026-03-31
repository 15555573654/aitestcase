"""
项目知识库服务：读写项目级业务知识 + AI 总结生成。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ....core.config import get_settings
from ....core.llm import LLMService

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parents[4] / "data" / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)


def _knowledge_path(project: str) -> Path:
    safe = project.replace("/", "_").replace("..", "_") or "default"
    return KNOWLEDGE_DIR / f"{safe}.md"


def get_knowledge(project: str) -> str:
    """读取项目知识库内容（markdown）。"""
    path = _knowledge_path(project)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def save_knowledge(project: str, content: str) -> None:
    """保存项目知识库内容。"""
    path = _knowledge_path(project)
    path.write_text(content, encoding="utf-8")
    logger.info("知识库已保存 | project=%s size=%d", project, len(content))


async def generate_knowledge_draft(
    project: str,
    requirement_text: str,
    summary_title: str,
    business_rules: list[str],
    test_points_summary: str,
    existing_knowledge: str,
) -> str:
    """
    基于当前任务的信息，AI 生成知识库补充草稿。
    QA 审核后再调用 save_knowledge 写入。
    """
    settings = get_settings()
    llm = LLMService(settings)

    system_prompt = """你是一名高级 QA 知识管理专家，负责从测试任务中提取可复用的业务知识。

你的输出将作为项目知识库的补充内容，供后续测试任务参考。

──── 提取规则 ────
只提取以下类型的信息：
1. 通用业务规则（如"所有删除为软删除""金额精确到分"）
2. 状态机和状态流转（如"订单状态：待支付→已支付→已完成→已退款"）
3. 跨模块依赖（如"用户封禁时关联订阅需暂停"）
4. 接口约定（如"status=1 成功 / status=2 失败"）
5. 历史踩坑点（如"并发场景下库存超卖"）

──── 禁止 ────
• 不要重复 PRD 原文
• 不要写具体的测试用例
• 不要写只适用于当前版本、不可复用的临时信息

──── 输出格式 ────
输出标准 Markdown，用二级标题分类，每条规则一行。
如果现有知识库已有内容，只输出新增/修改的部分，用 [新增] 或 [更新] 标注。"""

    existing_section = ""
    if existing_knowledge.strip():
        existing_section = f"\n────── 现有知识库内容 ──────\n{existing_knowledge}\n"

    user_prompt = f"""当前任务信息：
标题：{summary_title}
项目：{project}

业务规则：
{chr(10).join(f'- {r}' for r in business_rules)}

测试点概要：
{test_points_summary}

需求文本（节选前 2000 字）：
{requirement_text[:2000]}
{existing_section}
请提取可沉淀到项目知识库的业务知识。"""

    raw = await llm.generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_schema={"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
        temperature=0.1,
    )
    return raw.get("content", "")
