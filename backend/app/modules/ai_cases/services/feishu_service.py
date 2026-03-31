"""
飞书文档服务：tenant_access_token 鉴权 + 文档内容获取 + blocks 转 Markdown。
"""
from __future__ import annotations

import base64
import logging
import re
import time
from typing import Any

import httpx

from ....core.config import get_settings

logger = logging.getLogger(__name__)

FEISHU_BASE = "https://open.feishu.cn/open-apis"
_tenant_token_cache: dict[str, Any] = {"access_token": "", "expires_at": 0.0}


def _get_tenant_access_token() -> str:
    cached_token = _tenant_token_cache.get("access_token")
    if cached_token and time.time() < _tenant_token_cache.get("expires_at", 0):
        return cached_token

    settings = get_settings()
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": settings.feishu_app_id, "app_secret": settings.feishu_app_secret},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"获取 tenant_access_token 失败: {data.get('msg')}")
        access_token = data["tenant_access_token"]
        _tenant_token_cache["access_token"] = access_token
        _tenant_token_cache["expires_at"] = time.time() + data.get("expire", 7200) - 60
        return access_token


# ─────────────────────────────────────────────
# 文档获取
# ─────────────────────────────────────────────

def extract_doc_reference(url: str) -> tuple[str, str]:
    """从飞书链接提取资源类型和 token。"""
    match = re.search(r"/(?P<kind>docx|wiki|docs)/(?P<token>[a-zA-Z0-9]+)", url)
    if not match:
        raise ValueError(f"无法从 URL 中提取文档 ID: {url}")
    kind = match.group("kind")
    token = match.group("token")
    if kind == "wiki":
        return "wiki", token
    return "docx", token


def _api_get(path: str, access_token: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{FEISHU_BASE}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            raise ValueError(f"飞书 API 返回非 JSON: {resp.text[:200]}")
        if data.get("code") != 0:
            code = data.get("code")
            msg = data.get("msg")
            if code == 99991672 and path.startswith("/wiki/"):
                raise ValueError(
                    "飞书 Wiki 权限不足，请在应用权限中开通 "
                    "`wiki:node:read` 或 `wiki:wiki:readonly`。"
                    f" 原始错误: {msg} (code={code})"
                )
            raise ValueError(f"飞书 API 错误: {msg} (code={code})")
        return data.get("data", {})


def get_document_blocks(doc_id: str, access_token: str) -> list[dict]:
    """获取文档所有 blocks（自动翻页）。"""
    blocks: list[dict] = []
    page_token = None
    while True:
        params: dict[str, Any] = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = _api_get(f"/docx/v1/documents/{doc_id}/blocks", access_token, params)
        blocks.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return blocks


def get_document_meta(doc_id: str, access_token: str) -> dict:
    """获取文档标题等元信息。"""
    return _api_get(f"/docx/v1/documents/{doc_id}", access_token)


def get_wiki_node(token: str, access_token: str) -> dict:
    """获取 wiki 节点信息，用于解析真实的文档对象 token。"""
    return _api_get("/wiki/v2/spaces/get_node", access_token, {"token": token})


def resolve_document_id(doc_url: str, access_token: str) -> tuple[str, str]:
    """
    解析飞书链接，返回 (document_id, source_type)。

    - docx/docs 链接: 直接返回 token
    - wiki 链接: 先解析节点，再取实际 docx 的 obj_token
    """
    source_type, token = extract_doc_reference(doc_url)
    if source_type != "wiki":
        return token, source_type

    node_data = get_wiki_node(token, access_token)
    node = node_data.get("node", node_data)
    obj_type = node.get("obj_type", "")
    obj_token = node.get("obj_token", "")
    if not obj_token:
        raise ValueError("未能从 Wiki 节点解析出实际文档 token")
    if obj_type != "docx":
        raise ValueError(f"当前 Wiki 节点类型为 `{obj_type or 'unknown'}`，暂仅支持导入 docx 文档")
    return obj_token, source_type


def download_image(file_token: str, access_token: str) -> str:
    """下载图片并返回 base64 data URL。"""
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{FEISHU_BASE}/drive/v1/medias/{file_token}/download",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png")
        b64 = base64.b64encode(resp.content).decode()
        return f"data:{content_type};base64,{b64}"


# ─────────────────────────────────────────────
# Blocks → Markdown
# ─────────────────────────────────────────────

def _text_elements_to_str(elements: list[dict]) -> str:
    parts = []
    for elem in elements:
        if "text_run" in elem:
            parts.append(elem["text_run"].get("content", ""))
        elif "mention_user" in elem:
            parts.append("@用户")
    return "".join(parts)


def _text_elements_to_markdown(elements: list[dict]) -> str:
    parts: list[str] = []
    for elem in elements:
        if "text_run" in elem:
            tr = elem["text_run"]
            content = tr.get("content", "")
            style = tr.get("text_element_style", {})
            if style.get("inline_code"):
                content = f"`{content}`"
            if style.get("bold"):
                content = f"**{content}**"
            if style.get("italic"):
                content = f"*{content}*"
            if style.get("strikethrough"):
                content = f"~~{content}~~"
            if style.get("link"):
                url = style["link"].get("url", "")
                if url:
                    label = content or url
                    content = f"[{label}]({url})"
            parts.append(content)
        elif "mention_user" in elem:
            parts.append("@用户")
    return "".join(parts).strip()


def blocks_to_markdown(blocks: list[dict], access_token: str) -> str:
    # 构建 block_id → block 的查找表（表格解析需要）
    block_map: dict[str, dict] = {}
    for b in blocks:
        bid = b.get("block_id", "")
        if bid:
            block_map[bid] = b

    lines: list[str] = []
    skip_ids: set[str] = set()  # 已被表格消费的 cell block，跳过

    for block in blocks:
        bid = block.get("block_id", "")
        if bid in skip_ids:
            continue

        block_type = block.get("block_type")
        if block_type == 1:
            continue

        body = block.get(
            {
                2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
                6: "heading4", 7: "heading5", 8: "heading6", 9: "heading7",
                10: "heading8", 11: "heading9",
                12: "bullet", 13: "ordered", 14: "code", 15: "quote",
                17: "todo",
            }.get(block_type, ""),
            {},
        )
        elements = body.get("elements", [])

        if block_type in range(3, 12):
            level = block_type - 2
            text = _text_elements_to_markdown(elements)
            if text:
                lines.append(f"{'#' * min(level, 6)} {text}")
        elif block_type == 2:
            text = _text_elements_to_markdown(elements)
            if text:
                lines.append(text)
        elif block_type == 12:
            text = _text_elements_to_markdown(elements)
            if text:
                lines.append(f"- {text}")
        elif block_type == 13:
            text = _text_elements_to_markdown(elements)
            if text:
                lines.append(f"1. {text}")
        elif block_type == 14:
            text = _text_elements_to_str(elements)
            if text.strip():
                lines.append(f"```\n{text}\n```")
        elif block_type == 15:
            text = _text_elements_to_markdown(elements)
            if text:
                lines.append(f"> {text}")
        elif block_type == 17:
            text = _text_elements_to_markdown(elements)
            if text:
                done = body.get("style", {}).get("done", False)
                lines.append(f"- [{'x' if done else ' '}] {text}")
        elif block_type == 27:
            image_body = block.get("image", {})
            file_token = image_body.get("token", "")
            if file_token:
                try:
                    data_url = download_image(file_token, access_token)
                    lines.append(f"![图片]({data_url})")
                except Exception as exc:
                    logger.warning("下载图片失败 %s: %s", file_token, exc)
                    lines.append("![图片加载失败]()")
        elif block_type == 18:
            # ── 表格 ──
            table_body = block.get("table", {})
            table_property = table_body.get("property", {})
            row_size = table_property.get("row_size", 0)
            col_size = table_property.get("column_size", 0)
            cells = table_body.get("cells", [])  # 一维数组，按行优先排列

            if cells and row_size and col_size:
                table_lines: list[str] = []
                for row_idx in range(row_size):
                    row_cells: list[str] = []
                    for col_idx in range(col_size):
                        cell_idx = row_idx * col_size + col_idx
                        if cell_idx < len(cells):
                            cell_id = cells[cell_idx]
                            skip_ids.add(cell_id)
                            # cell block 的子 block 包含实际文本
                            cell_block = block_map.get(cell_id, {})
                            cell_text = _extract_cell_text(cell_block, block_map, skip_ids)
                            row_cells.append(cell_text.replace("|", "\\|").replace("\n", " "))
                        else:
                            row_cells.append("")
                    table_lines.append("| " + " | ".join(row_cells) + " |")
                    if row_idx == 0:
                        table_lines.append("| " + " | ".join(["---"] * col_size) + " |")
                lines.append("\n".join(table_lines))
        else:
            text = _text_elements_to_markdown(elements)
            if text:
                lines.append(text)

    return "\n\n".join(line for line in lines if line.strip())


def _extract_cell_text(cell_block: dict, block_map: dict[str, dict], skip_ids: set[str]) -> str:
    """从表格 cell block 及其子 block 中提取文本。"""
    parts: list[str] = []
    # cell 本身可能有 text
    children_ids = cell_block.get("children", [])
    for child_id in children_ids:
        skip_ids.add(child_id)
        child = block_map.get(child_id, {})
        child_type = child.get("block_type")
        body_key = {2: "text", 12: "bullet", 13: "ordered"}.get(child_type, "text")
        body = child.get(body_key, {})
        elements = body.get("elements", [])
        text = _text_elements_to_str(elements)
        if text.strip():
            parts.append(text.strip())
    if not parts:
        # fallback：直接从 cell block 提取
        body = cell_block.get("text", {})
        elements = body.get("elements", [])
        text = _text_elements_to_str(elements)
        if text.strip():
            parts.append(text.strip())
    return " ".join(parts) if parts else ""


# ─────────────────────────────────────────────
# 高级接口
# ─────────────────────────────────────────────

def fetch_document(doc_url: str) -> dict[str, Any]:
    """
    完整获取飞书文档。
    返回:
    - title: 文档标题
    - markdown: 完整 markdown（含图片 base64，用于前端预览）
    - text: 纯文本版（图片替换为 [图片N] 占位符，用于 AI prompt）
    - images: 图片数组 [{index, data_url, context}]，用于多模态 AI
    - images_count: 图片数量
    - source_type: 来源类型
    """
    access_token = _get_tenant_access_token()
    doc_id, source_type = resolve_document_id(doc_url, access_token)
    logger.info("获取飞书文档: source_type=%s doc_id=%s", source_type, doc_id)

    meta = get_document_meta(doc_id, access_token)
    title = meta.get("document", {}).get("title", "")

    blocks = get_document_blocks(doc_id, access_token)
    logger.info("文档 blocks 数量: %d", len(blocks))

    markdown = blocks_to_markdown(blocks, access_token)

    # markdown 中图片替换为占位符（base64 太大不适合编辑）
    images: list[dict[str, Any]] = []
    img_pattern = re.compile(r'!\[图片\]\(data:[^)]+\)')
    clean_markdown = markdown

    img_idx = 0
    for match in img_pattern.finditer(markdown):
        img_idx += 1
        data_url = match.group(0)[len("![图片]("):-1]
        start = max(0, match.start() - 80)
        end = min(len(markdown), match.end() + 80)
        context_before = markdown[start:match.start()].strip().split("\n")[-1]
        context_after = markdown[match.end():end].strip().split("\n")[0]
        images.append({
            "index": img_idx,
            "data_url": data_url,
            "context": f"位于「{context_before}」和「{context_after}」之间",
        })

    counter = [0]
    def _replace_img(m: re.Match) -> str:
        counter[0] += 1
        return f"[图片{counter[0]}]"
    clean_markdown = img_pattern.sub(_replace_img, markdown)

    return {
        "title": title,
        "markdown": clean_markdown,
        "images": images,
        "images_count": len(images),
        "source_type": source_type,
    }