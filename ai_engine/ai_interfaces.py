from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ai_engine.ai_types import AIRequest, AIResponse


class AIProviderInterface(ABC):
    name: str = "base"

    @abstractmethod
    def supports(self, task: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError


class RetryPolicyInterface(ABC):
    @abstractmethod
    def should_retry(self, attempt: int, error: Exception) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delay_for_attempt(self, attempt: int) -> float:
        raise NotImplementedError


class ModelSelectorInterface(ABC):
    @abstractmethod
    def select_model(self, task: str, preferred: Optional[str] = None) -> Optional[str]:
        raise NotImplementedError


class StructuredResponseValidator(ABC):
    @abstractmethod
    def validate(self, response: AIResponse, required_fields: Optional[List[str]] = None) -> bool:
        raise NotImplementedError


class AIProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, AIProviderInterface] = {}

    def register_provider(self, provider: AIProviderInterface) -> None:
        self._providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[AIProviderInterface]:
        return self._providers.get(name)

    def select_provider(self, task: str, preferred: Optional[str] = None) -> Optional[AIProviderInterface]:
        if preferred and preferred in self._providers:
            return self._providers[preferred]

        for provider in self._providers.values():
            if provider.supports(task):
                return provider
        return None

    @property
    def providers(self) -> List[AIProviderInterface]:
        return list(self._providers.values())


class DefaultRetryPolicy(RetryPolicyInterface):
    def should_retry(self, attempt: int, error: Exception) -> bool:
        if attempt >= 3:
            return False
        return isinstance(error, (TimeoutError, ConnectionError, OSError))

    def delay_for_attempt(self, attempt: int) -> float:
        return min(0.25 * (2 ** max(attempt - 1, 0)), 2.0)


class DefaultModelSelector(ModelSelectorInterface):
    def select_model(self, task: str, preferred: Optional[str] = None) -> Optional[str]:
        if preferred:
            return preferred

        model_map = {
            "job_description_understanding": "gpt-4o-mini",
            "skill_extraction": "gpt-4o-mini",
            "role_classification": "gpt-4o-mini",
            "candidate_job_explanation": "gpt-4o-mini",
            "resume_tailoring_suggestions": "gpt-4o-mini",
            "ats_improvement_suggestions": "gpt-4o-mini",
        }
        return model_map.get(task, "default-model")


class JsonSchemaValidator(StructuredResponseValidator):
    def validate(self, response: AIResponse, required_fields: Optional[List[str]] = None) -> bool:
        if not response.success:
            return False
        if not isinstance(response.payload, dict):
            return False

        required = required_fields or []
        if not required:
            return True

        if "result" in response.payload and isinstance(response.payload["result"], dict):
            result_payload = response.payload["result"]
            return all(field in result_payload for field in required if field in result_payload) or all(field in response.payload for field in required)

        return all(field in response.payload for field in required)
