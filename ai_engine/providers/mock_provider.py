from __future__ import annotations

from ai_engine.ai_interfaces import AIProviderInterface
from ai_engine.ai_types import AIRequest, AIResponse


class MockAIProvider(AIProviderInterface):
    name = "mock"

    def __init__(self, name: str = "mock"):
        self.name = name

    def supports(self, task: str) -> bool:
        return True

    def generate(self, request: AIRequest) -> AIResponse:
        if request.task == "job_description_understanding":
            payload = {
                "job_role": request.payload.get("job_title") or request.payload.get("title") or "Embedded Engineer",
                "skills": [
                    "Embedded C",
                    "C",
                    "Linux",
                    "ARM",
                    "GPIO",
                ],
                "missing_skills": [],
                "experience_fit": "fresher",
                "location_fit": True,
            }
        elif request.task == "skill_extraction":
            payload = {
                "skills": ["Embedded C", "Linux", "ARM", "GPIO"],
                "missing_skills": [],
            }
        elif request.task == "role_classification":
            payload = {
                "role": "Embedded Linux Engineer",
                "confidence": 0.98,
            }
        else:
            payload = {
                "result": {
                    "task": request.task,
                    "status": "ok",
                }
            }

        return AIResponse(
            success=True,
            task=request.task,
            provider=self.name,
            model=request.model or "mock-model",
            payload=payload,
        )
