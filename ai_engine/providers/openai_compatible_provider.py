from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests

from ai_engine.ai_interfaces import AIProviderInterface
from ai_engine.ai_types import AIRequest, AIResponse
from config.settings import settings

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(AIProviderInterface):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, default_model: Optional[str] = None, timeout_seconds: float = 10.0, max_retries: int = 2):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "") or ""
        self.base_url = base_url or os.getenv("OPENAI_API_BASE_URL") or getattr(settings, "OPENAI_API_BASE_URL", "https://api.openai.com/v1")
        self.default_model = default_model or os.getenv("OPENAI_DEFAULT_MODEL") or getattr(settings, "OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
        self.timeout_seconds = float(timeout_seconds or getattr(settings, "AI_TIMEOUT_SECONDS", 10.0))
        self.max_retries = int(max_retries or getattr(settings, "AI_MAX_RETRIES", 2))
        self.enabled = bool(self.api_key)

    @classmethod
    def from_settings(cls):
        api_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            base_url=getattr(settings, "OPENAI_API_BASE_URL", "https://api.openai.com/v1"),
            default_model=getattr(settings, "OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
            timeout_seconds=getattr(settings, "AI_TIMEOUT_SECONDS", 10.0),
            max_retries=getattr(settings, "AI_MAX_RETRIES", 2),
        )

    def supports(self, task: str) -> bool:
        return self.enabled and task in {
            "job_description_understanding",
            "skill_extraction",
            "role_classification",
            "candidate_job_explanation",
            "resume_tailoring_suggestions",
            "ats_improvement_suggestions",
        }

    def _build_payload(self, request: AIRequest) -> Dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": "You are a structured AI assistant for embedded engineering job analysis. Return valid JSON only.",
            },
            {
                "role": "user",
                "content": json.dumps({
                    "task": request.task,
                    "payload": request.payload,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "result": {"type": "object"},
                            "status": {"type": "string"},
                        },
                        "required": ["result", "status"],
                    },
                }),
            },
        ]

        return {
            "model": request.model or self.default_model,
            "messages": messages,
            "temperature": request.temperature or 0.2,
            "max_tokens": request.max_tokens or 512,
        }

    def _extract_json(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            stripped = content.strip()
            if stripped.startswith("```"):
                stripped = stripped.strip("`")
                if stripped.lower().startswith("json"):
                    stripped = stripped[4:].strip()
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                raise ValueError("AI response was not valid JSON")
        raise ValueError("AI response payload was not a JSON object")

    def generate(self, request: AIRequest) -> AIResponse:
        if not self.enabled:
            return AIResponse(
                success=False,
                task=request.task,
                provider=self.name,
                model=request.model or self.default_model,
                payload={},
                error="No OpenAI-compatible API key configured.",
                disabled=True,
            )

        started = time.time()
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                response = requests.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=self._build_payload(request),
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                payload = self._extract_json(content)
                return AIResponse(
                    success=True,
                    task=request.task,
                    provider=self.name,
                    model=request.model or self.default_model,
                    payload=payload,
                    latency_ms=int((time.time() - started) * 1000),
                )
            except (requests.RequestException, TimeoutError, ValueError, KeyError, TypeError) as exc:
                last_error = exc
                if attempt >= self.max_retries + 1:
                    break
                logger.warning("OpenAI-compatible provider attempt %s/%s failed: %s", attempt, self.max_retries + 1, exc)
                time.sleep(min(0.25 * (2 ** (attempt - 1)), 2.0))

        return AIResponse(
            success=False,
            task=request.task,
            provider=self.name,
            model=request.model or self.default_model,
            payload={},
            error=str(last_error) if last_error else "Unknown AI provider error",
            latency_ms=int((time.time() - started) * 1000),
        )
