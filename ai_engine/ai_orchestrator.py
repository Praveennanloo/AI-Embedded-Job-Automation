from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from ai_engine.ai_interfaces import AIProviderRegistry, DefaultModelSelector, DefaultRetryPolicy, JsonSchemaValidator
from ai_engine.ai_types import AIRequest, AIResponse

logger = logging.getLogger(__name__)


class AIConfig:
    def __init__(
        self,
        enabled: bool = False,
        default_provider: Optional[str] = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        default_model: Optional[str] = None,
        required_fields: Optional[list[str]] = None,
    ):
        self.enabled = enabled
        self.default_provider = default_provider
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.default_model = default_model
        self.required_fields = required_fields or []


class AIOrchestrator:
    def __init__(self, config: Optional[AIConfig] = None, registry: Optional[AIProviderRegistry] = None):
        self.config = config or AIConfig()
        self.registry = registry or AIProviderRegistry()
        self.retry_policy = DefaultRetryPolicy()
        self.model_selector = DefaultModelSelector()
        self.validator = JsonSchemaValidator()

    def run(self, task: str, payload: Dict[str, Any], model: Optional[str] = None) -> AIResponse:
        if not self.config.enabled:
            return AIResponse(
                success=False,
                task=task,
                provider="disabled",
                model=model or self.config.default_model or "disabled",
                payload={},
                error="AI provider is disabled.",
                disabled=True,
            )

        provider = self.registry.select_provider(task, self.config.default_provider)
        if provider is None:
            return AIResponse(
                success=False,
                task=task,
                provider="none",
                model=model or self.config.default_model or "unknown",
                payload={},
                error="No AI provider configured for this task.",
            )

        selected_model = model or self.model_selector.select_model(task, self.config.default_model)
        request = AIRequest(task=task, payload=payload, model=selected_model)
        started = time.time()

        try:
            response = provider.generate(request)
            response.latency_ms = int((time.time() - started) * 1000)

            required_fields = self.config.required_fields or ["result"]
            if not self.validator.validate(response, required_fields):
                return AIResponse(
                    success=False,
                    task=task,
                    provider=provider.name,
                    model=response.model,
                    payload=response.payload,
                    error="Malformed AI response payload.",
                    latency_ms=response.latency_ms,
                )
            return response
        except TimeoutError as exc:
            logger.warning("AI call timed out: %s", exc)
            return AIResponse(
                success=False,
                task=task,
                provider=provider.name,
                model=selected_model or "unknown",
                payload={},
                error=f"Timeout: {exc}",
                latency_ms=int((time.time() - started) * 1000),
            )
        except Exception as exc:
            logger.warning("AI call failed: %s", exc)
            return AIResponse(
                success=False,
                task=task,
                provider=provider.name,
                model=selected_model or "unknown",
                payload={},
                error=str(exc),
                latency_ms=int((time.time() - started) * 1000),
            )

    def safe_job_analysis(self, job, profile: Optional[Dict[str, Any]] = None):
        if not self.config.enabled:
            from ai_engine.job_filter import JobFilter
            return JobFilter().analyze_job_intelligence(job, profile or {})

        payload = {"job": job.__dict__ if hasattr(job, "__dict__") else {}, "profile": profile or {}}
        response = self.run(task="job_description_understanding", payload=payload)
        if response.success and isinstance(response.payload, dict):
            return response.payload

        from ai_engine.job_filter import JobFilter
        return JobFilter().analyze_job_intelligence(job, profile or {})
