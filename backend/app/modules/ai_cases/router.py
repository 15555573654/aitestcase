import logging
import traceback

import pymupdf
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from .models import (
    AnalyzeStructureRequest,
    AnalyzeStructureResponse,
    ClarifyRequest,
    ClarifyResponse,
    GenerateCasesRequest,
    GenerateCasesResponse,
    GenerateTestPointsRequest,
    GenerateTestPointsResponse,
    HistoryRecord,
    IntegrationTestsRequest,
    IntegrationTestsResponse,
    ReviewTestPointsRequest,
    ReviewTestPointsResponse,
)
from .services.history_service import HistoryService
from .services.workflow_service import WorkflowService, WorkflowValidationError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI 测试用例"])
workflow_service = WorkflowService()
history_service = HistoryService()


def _err_detail(label: str, exc: Exception) -> str:
    msg = str(exc) or f"{type(exc).__name__}: 请查看后端日志"
    return f"{label}：{msg}"


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")
    try:
        raw = await file.read()
        if len(raw) < 100:
            raise HTTPException(status_code=400, detail="文件内容过小，可能不是有效的 PDF")
        size_mb = len(raw) / (1024 * 1024)
        if size_mb > 50:
            raise HTTPException(status_code=400, detail=f"文件 {size_mb:.1f} MB，超过 50 MB 上限")
        logger.info("收到 PDF: %s, 大小: %.1f MB", file.filename, size_mb)
        doc = pymupdf.open(stream=raw, filetype="pdf")
        pages_text: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages_text.append(text)
        doc.close()
        if not pages_text:
            raise HTTPException(status_code=422, detail="PDF 中未提取到文本内容")
        extracted = "\n\n".join(pages_text)
        logger.info("PDF 文本提取完成: %d 页, %d 字符", len(pages_text), len(extracted))
        return {"text": extracted, "pages": len(pages_text)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("PDF 解析失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=_err_detail("PDF 解析失败", exc)) from exc


@router.post("/workflow/clarify", response_model=ClarifyResponse)
async def clarify(payload: ClarifyRequest) -> ClarifyResponse:
    try:
        return await workflow_service.clarify(payload)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail=_err_detail("需求澄清失败", exc)) from exc
    except Exception as exc:
        logger.error("clarify 失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=_err_detail("需求澄清失败", exc)) from exc


@router.post("/workflow/analyze-structure", response_model=AnalyzeStructureResponse)
async def analyze_structure(payload: AnalyzeStructureRequest) -> AnalyzeStructureResponse:
    try:
        return await workflow_service.analyze_structure(payload)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail=_err_detail("结构分析失败", exc)) from exc
    except Exception as exc:
        logger.error("analyze-structure 失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=_err_detail("结构分析失败", exc)) from exc


@router.post("/workflow/generate-test-points", response_model=GenerateTestPointsResponse)
async def generate_test_points(payload: GenerateTestPointsRequest) -> GenerateTestPointsResponse:
    try:
        return await workflow_service.generate_test_points(payload)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail=_err_detail("测试点生成失败", exc)) from exc
    except Exception as exc:
        logger.error("generate-test-points 失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=_err_detail("测试点生成失败", exc)) from exc


@router.post("/workflow/generate-cases", response_model=GenerateCasesResponse)
async def generate_cases(payload: GenerateCasesRequest) -> GenerateCasesResponse:
    try:
        return await workflow_service.generate_cases(payload)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail=_err_detail("测试用例生成失败", exc)) from exc
    except Exception as exc:
        logger.error("generate-cases 失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=_err_detail("测试用例生成失败", exc)) from exc


@router.post("/workflow/review-test-points", response_model=ReviewTestPointsResponse)
async def review_test_points(payload: ReviewTestPointsRequest) -> ReviewTestPointsResponse:
    try:
        return await workflow_service.review_test_points(payload)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail=_err_detail("测试点审核失败", exc)) from exc
    except Exception as exc:
        logger.error("review-test-points 失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=_err_detail("测试点审核失败", exc)) from exc


@router.post("/workflow/integration-tests", response_model=IntegrationTestsResponse)
async def integration_tests(payload: IntegrationTestsRequest) -> IntegrationTestsResponse:
    try:
        return await workflow_service.generate_integration_tests(payload)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail=_err_detail("联动测试生成失败", exc)) from exc
    except Exception as exc:
        logger.error("integration-tests 失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=_err_detail("联动测试生成失败", exc)) from exc


@router.get("/history", response_model=list[HistoryRecord])
async def list_history() -> list[HistoryRecord]:
    return history_service.list_records()


@router.post("/history", response_model=HistoryRecord)
async def save_history(record: HistoryRecord) -> HistoryRecord:
    return history_service.save_record(record)


@router.get("/history/{record_id}", response_model=HistoryRecord)
async def get_history(record_id: str) -> HistoryRecord:
    record = history_service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.delete("/history/{record_id}")
async def delete_history(record_id: str) -> dict[str, str]:
    if not history_service.delete_record(record_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"status": "ok"}


# ── 飞书文档导入 ──

from .services import feishu_service  # noqa: E402


class FeishuFetchRequest(BaseModel):
    doc_url: str


@router.post("/feishu/fetch-doc")
async def feishu_fetch_doc(req: FeishuFetchRequest):
    try:
        result = feishu_service.fetch_document(req.doc_url)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("飞书文档获取失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=f"文档获取失败：{exc}") from exc


# ── 项目知识库 ──

from .services import knowledge_service  # noqa: E402


class KnowledgeSaveRequest(BaseModel):
    project: str
    content: str


class KnowledgeDraftRequest(BaseModel):
    project: str
    requirement_text: str = ""
    summary_title: str = ""
    business_rules: list[str] = []
    test_points_summary: str = ""


@router.get("/knowledge/{project}")
async def get_knowledge(project: str):
    content = knowledge_service.get_knowledge(project)
    return {"project": project, "content": content}


@router.post("/knowledge")
async def save_knowledge(req: KnowledgeSaveRequest):
    knowledge_service.save_knowledge(req.project, req.content)
    return {"status": "ok"}


@router.post("/knowledge/generate-draft")
async def generate_knowledge_draft(req: KnowledgeDraftRequest):
    try:
        existing = knowledge_service.get_knowledge(req.project)
        draft = await knowledge_service.generate_knowledge_draft(
            project=req.project,
            requirement_text=req.requirement_text,
            summary_title=req.summary_title,
            business_rules=req.business_rules,
            test_points_summary=req.test_points_summary,
            existing_knowledge=existing,
        )
        return {"draft": draft, "existing": existing}
    except Exception as exc:
        logger.error("知识库草稿生成失败:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=f"生成失败：{exc}") from exc
