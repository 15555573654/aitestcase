from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date


# ---------- 通用响应 ----------

class PictureItem(BaseModel):
    question_id: Optional[str] = None
    picture_key: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    task_type: Optional[str] = None
    create_time: Optional[str] = None
    image_url: Optional[str] = None


class QuestionDetail(BaseModel):
    question_id: Optional[str] = None
    device_id: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    task_type: Optional[str] = None
    question_text: Optional[str] = None
    answer: Optional[str] = None
    picture_key: Optional[str] = None
    create_time: Optional[str] = None
    image_url: Optional[str] = None


class FilterOptions(BaseModel):
    languages: List[str] = []
    subjects: List[str] = []
    task_types: List[str] = []


# ---------- 请求体 ----------

class SearchByFiltersRequest(BaseModel):
    language: Optional[str] = Field(None, description="语言代码，如 en/zh/es")
    subject: Optional[str] = Field(None, description="学科")
    task_type: Optional[str] = Field(None, description="任务类型")
    start_date: Optional[date] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[date] = Field(None, description="结束日期 YYYY-MM-DD")
    limit: int = Field(50, ge=1, le=100, description="返回条数，最大100")
    offset: int = Field(0, ge=0)


class SearchByIdRequest(BaseModel):
    question_id: Optional[str] = Field(None, description="题目ID")
    device_id: Optional[str] = Field(None, description="设备ID")
    limit: int = Field(20, ge=1, le=100)


# ---------- Flashcards ----------

class FlashcardResource(BaseModel):
    uid: Optional[str] = None
    deck_id: Optional[str] = None
    name: Optional[str] = None
    resource_type: Optional[str] = None
    origin_url: Optional[str] = None
    parsed_url: Optional[str] = None
    selected_page_index: Optional[str] = None
    platform: Optional[str] = None
    create_at: Optional[str] = None
    update_at: Optional[str] = None
    deleted_at: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None


class FlashcardsSearchRequest(BaseModel):
    resource_type: Optional[str] = Field(None, description="资源类型，如 PDF/PPT/WORD/TXT")
    uid: Optional[str] = Field(None, description="用户 ID")
    platform: Optional[str] = Field(None, description="平台，如 web/iOS/unknown")
    status: Optional[str] = Field(None, description="状态")
    start_date: Optional[date] = Field(None, description="创建时间起始 YYYY-MM-DD")
    end_date: Optional[date] = Field(None, description="创建时间截止 YYYY-MM-DD")
    include_deleted: bool = Field(False, description="是否包含已软删除的数据")
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class FlashcardsCountResult(BaseModel):
    resource_type: str
    count: int


# ---------- Agent ----------

class AgentChatMessage(BaseModel):
    role: str  # "user" or "model"
    content: str


class AgentRequest(BaseModel):
    message: str
    history: List[AgentChatMessage] = []


class AgentResponse(BaseModel):
    reply: str
    results: Optional[List[Any]] = None
    sql_executed: Optional[str] = None
    result_type: Optional[str] = None  # "pictures" | "questions" | "text"
