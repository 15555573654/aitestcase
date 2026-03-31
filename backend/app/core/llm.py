from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)

# LLM 单次调用的超时时间（秒）
LLM_TIMEOUT_SECONDS = 30000  # 5 分钟00


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._gemini_client = None
        self._openai_client = None

    @property
    def provider(self) -> str:
        return self.settings.llm_provider.lower()

    @property
    def gemini_client(self):
        if self._gemini_client is None:
            from google import genai
            if not self.settings.llm_api_key:
                raise RuntimeError("未配置 LLM_API_KEY。")
            self._gemini_client = genai.Client(api_key=self.settings.llm_api_key)
        return self._gemini_client

    @property
    def openai_client(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI
            if not self.settings.llm_api_key:
                raise RuntimeError("未配置 LLM_API_KEY。")
            self._openai_client = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url or None,
            )
        return self._openai_client

    @property
    def model(self) -> str:
        if not self.settings.llm_model:
            raise RuntimeError("未配置 LLM_MODEL。")
        return self.settings.llm_model

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        temperature: float | None = None,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        """调用 LLM 生成结构化 JSON 输出。支持多模态（文本+图片）。"""
        actual_temperature = temperature if temperature is not None else self.settings.llm_temperature
        logger.info(
            "LLM 请求开始 | provider=%s model=%s temperature=%s images=%d",
            self.provider, self.model, actual_temperature, len(images or [])
        )
        logger.debug("system_prompt=%s", system_prompt)
        logger.debug("user_prompt=%s", user_prompt)

        if self.provider == "gemini":
            return await self._generate_json_gemini(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=json_schema,
                temperature=actual_temperature,
                images=images,
            )
        elif self.provider == "openai":
            return await self._generate_json_openai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=json_schema,
                temperature=actual_temperature,
                images=images,
            )
        else:
            raise ValueError(f"不支持的 LLM provider: {self.provider}")

    # ------------------------------------------------------------------ #
    # Gemini Implementation
    # ------------------------------------------------------------------ #

    async def _generate_json_gemini(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        temperature: float,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        from google.genai import types

        contents = self._build_gemini_contents(user_prompt, images)

        try:
            response = await asyncio.wait_for(
                self.gemini_client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_json_schema=json_schema,
                    ),
                ),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("LLM 请求超时 | timeout=%ds", LLM_TIMEOUT_SECONDS)
            raise TimeoutError(f"LLM 请求超时（{LLM_TIMEOUT_SECONDS}s），请稍后重试。")

        usage = getattr(response, "usage_metadata", None)
        if usage:
            logger.info(
                "LLM 请求完成 | input_tokens=%s output_tokens=%s total_tokens=%s",
                getattr(usage, "prompt_token_count", "?"),
                getattr(usage, "candidates_token_count", "?"),
                getattr(usage, "total_token_count", "?"),
            )
        else:
            logger.info("LLM 请求完成")

        return self._parse_json_response(response.text or "")

    @staticmethod
    def _build_gemini_contents(user_prompt: str, images: list[str] | None = None) -> Any:
        """构建 Gemini contents。"""
        if not images:
            return user_prompt

        import base64
        from google.genai import types

        parts: list[Any] = [user_prompt]
        for i, data_url in enumerate(images):
            try:
                if data_url.startswith("data:"):
                    header, b64data = data_url.split(",", 1)
                    mime_type = header.split(":")[1].split(";")[0]
                else:
                    b64data = data_url
                    mime_type = "image/png"
                img_bytes = base64.b64decode(b64data)
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
                logger.debug("添加图片 %d | mime=%s size=%d bytes", i + 1, mime_type, len(img_bytes))
            except Exception as e:
                logger.warning("解析图片 %d 失败: %s", i + 1, e)
        return parts

    # ------------------------------------------------------------------ #
    # OpenAI Implementation (支持 DeepSeek 等兼容 API)
    # ------------------------------------------------------------------ #

    async def _generate_json_openai(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        temperature: float,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        """使用 OpenAI 兼容 API 生成 JSON（支持 DeepSeek）。"""
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # 构建用户消息（支持图片）
        if images:
            content = [{"type": "text", "text": user_prompt}]
            for img_url in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_url}
                })
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": user_prompt})

        try:
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                ),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("LLM 请求超时 | timeout=%ds", LLM_TIMEOUT_SECONDS)
            raise TimeoutError(f"LLM 请求超时（{LLM_TIMEOUT_SECONDS}s），请稍后重试。")

        usage = response.usage
        if usage:
            logger.info(
                "LLM 请求完成 | input_tokens=%s output_tokens=%s total_tokens=%s",
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )
        else:
            logger.info("LLM 请求完成")

        content = response.choices[0].message.content or ""
        return self._parse_json_response(content)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        text = text.strip()

        if not text:
            logger.error("LLM 返回内容为空")
            raise ValueError("LLM 返回内容为空")

        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            result = json.loads(text)
            logger.debug("JSON 解析成功 | keys=%s", list(result.keys()) if isinstance(result, dict) else type(result).__name__)
            return result
        except json.JSONDecodeError as e:
            logger.error("JSON 解析失败 | error=%s | 原文前 200 字=%s", e, text[:200])
            raise ValueError(
                f"LLM 返回 JSON 解析失败: {e}; 原文前 200 字: {text[:200]}"
            ) from e
