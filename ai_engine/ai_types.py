from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AIRequest:
    task: str
    payload: Dict[str, Any]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    success: bool
    task: str
    provider: str
    model: str
    payload: Dict[str, Any]
    error: Optional[str] = None
    latency_ms: Optional[int] = None
    request_id: Optional[str] = None
    disabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "task": self.task,
            "provider": self.provider,
            "model": self.model,
            "payload": self.payload,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "request_id": self.request_id,
            "disabled": self.disabled,
        }


@dataclass
class AIProviderConfig:
    name: str
    enabled: bool = False
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    timeout_seconds: float = 10.0
    max_retries: int = 2
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class AIJobAnalysis:
    role: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    experience_fit: Optional[str] = None
    location_fit: Optional[bool] = None
    summary: str = ""
    structured: Dict[str, Any] = field(default_factory=dict)
