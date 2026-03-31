import logging

from fastapi import APIRouter, HTTPException

from ...core.config import get_settings
from .models import (
    AgentRequest,
    AgentResponse,
    FilterOptions,
    FlashcardResource,
    FlashcardsCountResult,
    FlashcardsSearchRequest,
    PictureItem,
    QuestionDetail,
    SearchByFiltersRequest,
    SearchByIdRequest,
)
from .services.bigquery_service import get_bq_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["BQ 数据查询"])


def _get_source(source_key: str):
    settings = get_settings()
    sources = settings.bq_sources
    if source_key not in sources:
        raise HTTPException(status_code=404, detail=f"数据源 {source_key} 不存在")
    return sources[source_key]


@router.get("/sources", summary="获取所有可用数据源")
async def list_sources():
    settings = get_settings()
    return [
        {"key": src.key, "label": src.label, "project_id": src.project_id, "dataset": src.dataset, "table": src.table}
        for src in settings.bq_sources.values()
    ]


@router.get("/{source_key}/fields", summary="获取数据源字段列表")
async def get_fields(source_key: str):
    source = _get_source(source_key)
    svc = get_bq_service(source)
    try:
        return svc.get_table_fields()
    except Exception as e:
        logger.exception("获取字段列表失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_key}/options", response_model=FilterOptions, summary="获取过滤选项")
async def get_filter_options(source_key: str):
    source = _get_source(source_key)
    svc = get_bq_service(source)
    try:
        # 对题目数据源使用固定字段，其他数据源动态获取
        if source_key == "questions":
            data = svc.get_filter_options(["language", "subject", "task_type"])
            return FilterOptions(
                languages=data.get("language", []),
                subjects=data.get("subject", []),
                task_types=data.get("task_type", []),
            )
        else:
            # 通用：返回所有 STRING 字段的过滤选项
            fields = svc.get_table_fields()
            string_fields = [f["name"] for f in fields if f["type"] in ("STRING", "string")][:6]
            data = svc.get_filter_options(string_fields, min_count=10)
            return FilterOptions(
                languages=data.get(string_fields[0], []) if len(string_fields) > 0 else [],
                subjects=data.get(string_fields[1], []) if len(string_fields) > 1 else [],
                task_types=data.get(string_fields[2], []) if len(string_fields) > 2 else [],
            )
    except Exception as e:
        logger.exception("获取过滤选项失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source_key}/search/pictures", response_model=list[PictureItem], summary="按条件查询")
async def search_pictures(source_key: str, req: SearchByFiltersRequest):
    source = _get_source(source_key)
    svc = get_bq_service(source)
    try:
        filters = {}
        if req.language:
            filters["language"] = req.language
        if req.subject:
            filters["subject"] = req.subject
        if req.task_type:
            filters["task_type"] = req.task_type
        if req.start_date:
            filters["create_time__gte"] = req.start_date.isoformat()
        if req.end_date:
            filters["create_time__lte"] = req.end_date.isoformat()

        select_fields = ["question_id", "picture_key", "subject", "language", "task_type",
                         "FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', create_time) AS create_time"]
        rows = svc.search(
            select_fields=select_fields,
            filters=filters,
            limit=req.limit,
            offset=req.offset,
            order_by="create_time DESC",
        )
        return [PictureItem(**{k: str(v) if v is not None else None for k, v in r.items()}) for r in rows]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("查询失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source_key}/question/lookup", response_model=list[QuestionDetail], summary="按ID查询")
async def lookup_question(source_key: str, req: SearchByIdRequest):
    source = _get_source(source_key)
    svc = get_bq_service(source)
    try:
        id_filters = {}
        if req.question_id:
            id_filters["question_id"] = req.question_id
        if req.device_id:
            id_filters["device_id"] = req.device_id

        select_fields = ["question_id", "device_id", "subject", "language", "task_type",
                         "question_text", "answer", "picture_key",
                         "FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', create_time) AS create_time"]
        rows = svc.search_by_id(id_filters=id_filters, select_fields=select_fields, limit=req.limit)
        return [QuestionDetail(**{k: str(v) if v is not None else None for k, v in r.items()}) for r in rows]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("查询失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flashcards/resource-types", summary="获取 Flashcards 可用资源类型列表")
async def get_flashcard_resource_types():
    source = _get_source("flashcards")
    svc = get_bq_service(source)
    try:
        sql = f"""
        SELECT resource_type, COUNT(*) AS cnt
        FROM {svc.table}
        WHERE resource_type IS NOT NULL AND TRIM(resource_type) != ''
        GROUP BY resource_type
        ORDER BY cnt DESC
        LIMIT 50
        """
        rows = svc.run_query(sql)
        return [{"resource_type": r["resource_type"], "count": int(r["cnt"])} for r in rows]
    except Exception as e:
        logger.exception("获取资源类型失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flashcards/search", response_model=list[FlashcardResource], summary="查询 Flashcards 资源")
async def search_flashcards(req: FlashcardsSearchRequest):
    source = _get_source("flashcards")
    svc = get_bq_service(source)
    try:
        from google.cloud import bigquery as bq_lib

        conditions: list[str] = []
        params: list = []

        if req.resource_type:
            conditions.append("resource_type = @resource_type")
            params.append(bq_lib.ScalarQueryParameter("resource_type", "STRING", req.resource_type))

        if req.uid:
            conditions.append("uid = @uid")
            params.append(bq_lib.ScalarQueryParameter("uid", "STRING", req.uid))

        if req.platform:
            conditions.append("platform = @platform")
            params.append(bq_lib.ScalarQueryParameter("platform", "STRING", req.platform))

        if req.status:
            conditions.append("status = @status")
            params.append(bq_lib.ScalarQueryParameter("status", "STRING", req.status))

        if req.start_date:
            conditions.append("DATE(create_at) >= @start_date")
            params.append(bq_lib.ScalarQueryParameter("start_date", "DATE", req.start_date.isoformat()))

        if req.end_date:
            conditions.append("DATE(create_at) <= @end_date")
            params.append(bq_lib.ScalarQueryParameter("end_date", "DATE", req.end_date.isoformat()))

        if not req.include_deleted:
            conditions.append("deleted_at IS NULL")

        if not conditions:
            raise ValueError("请至少提供一个查询条件")

        where_clause = " AND ".join(conditions)
        real_limit = min(req.limit, source.max_query_limit)

        sql = f"""
        SELECT
            uid,
            CAST(deck_id AS STRING) AS deck_id,
            name,
            resource_type,
            origin_url,
            parsed_url,
            selected_page_index,
            platform,
            FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', create_at) AS create_at,
            FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', update_at) AS update_at,
            CASE WHEN deleted_at IS NULL THEN NULL
                 ELSE FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', deleted_at) END AS deleted_at,
            source,
            status
        FROM {svc.table}
        WHERE {where_clause}
        ORDER BY create_at DESC
        LIMIT {real_limit} OFFSET {req.offset}
        """
        rows = svc.run_query(sql, params)

        result = []
        for r in rows:
            cleaned = {k: str(v) if v is not None else None for k, v in r.items()}
            result.append(FlashcardResource(**cleaned))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Flashcards 查询失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source_key}/agent/chat", response_model=AgentResponse, summary="AI 智能查询")
async def agent_chat(source_key: str, req: AgentRequest):
    source = _get_source(source_key)
    from .services import gemini_service
    try:
        history = [{"role": m.role, "content": m.content} for m in req.history]
        result = await gemini_service.agent_chat(
            source=source,
            message=req.message,
            history=history,
        )
        return AgentResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Agent 调用失败")
        raise HTTPException(status_code=500, detail=f"Agent 错误: {str(e)}")
