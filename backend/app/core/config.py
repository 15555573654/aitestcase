from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/ 目录路径，用于解析相对路径
BACKEND_DIR = str(Path(__file__).resolve().parents[2])


class BqSourceConfig(BaseModel):
    """单个 BQ 数据源配置。"""
    key: str
    label: str
    project_id: str
    dataset: str
    table: str
    key_path: str
    image_base_url: str = ""
    max_query_limit: int = 100

    @property
    def full_table_id(self) -> str:
        return f"`{self.project_id}.{self.dataset}.{self.table}`"

    def resolve_key_path(self) -> str:
        if os.path.isabs(self.key_path):
            return self.key_path
        return os.path.abspath(os.path.join(BACKEND_DIR, self.key_path))


class Settings(BaseSettings):
    """全局配置。"""
    app_name: str = "AI Test Platform API"
    app_env: str = "development"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # LLM（ai_cases 模块）
    llm_provider: str = "gemini"  # gemini 或 openai
    llm_api_key: str = ""
    llm_base_url: str = ""  # OpenAI 兼容 API 的 base_url（如 DeepSeek）
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.2

    # 飞书（ai_cases 模块 PRD 导入）
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    # BQ 数据源（bq_query 模块）
    bq_sources_json: str = "[]"

    # Gemini Agent（bq_query 模块）
    gemini_api_key: str = ""
    gemini_api_endpoint: str = ""
    https_proxy: str = ""

    @property
    def bq_sources(self) -> dict[str, BqSourceConfig]:
        try:
            raw_list = json.loads(self.bq_sources_json)
        except json.JSONDecodeError:
            return {}
        return {BqSourceConfig(**item).key: BqSourceConfig(**item) for item in raw_list}

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
