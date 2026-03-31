"""
Gemini Agent Service
使用 Function Calling 让 Gemini 自动选择并调用 BigQuery 查询工具。
支持多数据源：每次调用通过 source 参数决定查哪张表。
"""
import json
import logging
import os
from typing import List, Dict, Any, Optional

import google.generativeai as genai

from ....core.config import BqSourceConfig, get_settings
from .bigquery_service import get_bq_service

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_tools(source: BqSourceConfig) -> list:
    table_id = source.full_table_id
    return [
        {
            "name": "search_by_filters",
            "description": f"根据过滤条件查询 {table_id} 表中的数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "description": "要过滤的字段名"},
                    "value": {"type": "string", "description": "过滤值"},
                    "limit": {"type": "integer", "description": "返回条数，默认 20，最大 100"},
                },
                "required": [],
            },
        },
        {
            "name": "search_by_id",
            "description": "根据 ID 字段精确查询记录详情。",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "description": "ID 字段名，如 question_id、device_id"},
                    "value": {"type": "string", "description": "ID 值"},
                    "limit": {"type": "integer", "description": "返回条数，默认 20"},
                },
                "required": ["field", "value"],
            },
        },
        {
            "name": "get_filter_options",
            "description": "获取指定字段的可用过滤值列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "description": "要获取选项的字段名"},
                },
                "required": ["field"],
            },
        },
        {
            "name": "execute_custom_sql",
            "description": (
                f"执行自定义 SQL 查询。表名：{table_id}。"
                "只允许 SELECT 查询，必须包含 LIMIT 子句（最大100）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "完整的 BigQuery SQL SELECT 语句"},
                },
                "required": ["sql"],
            },
        },
    ]


def _build_system_prompt(source: BqSourceConfig, fields: List[Dict[str, str]]) -> str:
    table_id = source.full_table_id
    field_desc = "、".join(f"{f['name']}({f['type']})" for f in fields[:20])
    return f"""你是一个智能数据查询助手，帮助用户查询 BigQuery 数据库。

数据库表信息：
- 表名：{table_id}
- 字段：{field_desc}
- 查询时请务必加条件或限制数量

你的职责：
1. 理解用户的自然语言查询意图
2. 选择合适的工具执行查询
3. 用中文简洁地解释查询结果
4. 如果用户查询条件模糊，主动建议更精确的条件
"""


def _execute_tool(source: BqSourceConfig, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    svc = get_bq_service(source)
    logger.info("Agent [%s] 调用工具: %s, 参数: %s", source.key, tool_name, tool_args)

    if tool_name == "search_by_filters":
        field = tool_args.get("field", "")
        value = tool_args.get("value", "")
        limit = tool_args.get("limit", 20)
        if field and value:
            filters = {field: value}
        else:
            filters = {}
        rows = svc.search(select_fields=["*"], filters=filters, limit=limit)
        return {"type": "data", "data": rows, "count": len(rows)}

    elif tool_name == "search_by_id":
        field = tool_args.get("field", "question_id")
        value = tool_args.get("value", "")
        limit = tool_args.get("limit", 20)
        rows = svc.search_by_id(id_filters={field: value}, select_fields=["*"], limit=limit)
        return {"type": "data", "data": rows, "count": len(rows)}

    elif tool_name == "get_filter_options":
        field = tool_args.get("field", "")
        if not field:
            raise ValueError("请指定字段名")
        data = svc.get_filter_options([field], min_count=10)
        return {"type": "options", "data": data}

    elif tool_name == "execute_custom_sql":
        sql = tool_args.get("sql", "")
        rows = svc.execute_agent_query(sql)
        return {"type": "data", "data": rows, "count": len(rows), "sql": sql}

    else:
        raise ValueError(f"未知工具: {tool_name}")


def _get_gemini_model(source: BqSourceConfig):
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY 未配置")

    if settings.https_proxy:
        os.environ["HTTPS_PROXY"] = settings.https_proxy
        os.environ["HTTP_PROXY"] = settings.https_proxy

    client_options = {}
    if settings.gemini_api_endpoint:
        client_options["api_endpoint"] = settings.gemini_api_endpoint

    genai.configure(
        api_key=settings.gemini_api_key,
        transport="rest",
        client_options=client_options if client_options else None,
    )

    # 动态获取表字段
    try:
        svc = get_bq_service(source)
        fields = svc.get_table_fields()
    except Exception:
        fields = [{"name": "unknown", "type": "STRING"}]

    tools_def = _build_tools(source)
    tools = genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        k: genai.protos.Schema(
                            type=genai.protos.Type.STRING if v.get("type") == "string" else genai.protos.Type.INTEGER,
                            description=v.get("description", ""),
                        )
                        for k, v in t["parameters"].get("properties", {}).items()
                    },
                    required=t["parameters"].get("required", []),
                ),
            )
            for t in tools_def
        ]
    )

    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=_build_system_prompt(source, fields),
        tools=[tools],
    )


async def agent_chat(
    source: BqSourceConfig,
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    model = _get_gemini_model(source)

    chat_history = []
    for msg in (history or []):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "model") and content:
            chat_history.append({"role": role, "parts": [content]})

    chat = model.start_chat(history=chat_history)
    response = chat.send_message(message)

    tool_result_data = None
    sql_executed = None
    result_type = None
    final_reply = ""

    max_rounds = 3
    for _ in range(max_rounds):
        candidate = response.candidates[0]
        parts = candidate.content.parts
        function_calls = [p for p in parts if hasattr(p, "function_call") and p.function_call.name]
        if not function_calls:
            final_reply = "".join(p.text for p in parts if hasattr(p, "text") and p.text)
            break

        tool_responses = []
        for part in function_calls:
            fc = part.function_call
            try:
                tool_result = _execute_tool(source, fc.name, dict(fc.args))
                tool_result_data = tool_result.get("data")
                result_type = tool_result.get("type")
                sql_executed = tool_result.get("sql")
                tool_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": json.dumps(tool_result, ensure_ascii=False, default=str)},
                        )
                    )
                )
            except Exception as e:
                logger.error("工具执行失败: %s", e)
                tool_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"error": str(e)},
                        )
                    )
                )

        response = chat.send_message(tool_responses)

    if not final_reply:
        candidate = response.candidates[0]
        final_reply = "".join(p.text for p in candidate.content.parts if hasattr(p, "text") and p.text)

    return {
        "reply": final_reply or "查询完成",
        "results": tool_result_data,
        "sql_executed": sql_executed,
        "result_type": result_type,
    }
