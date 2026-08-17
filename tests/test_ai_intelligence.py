import pytest

from ai_engine.ai_orchestrator import AIConfig, AIOrchestrator, AIProviderRegistry, AIResponse
from ai_engine.ai_types import AIRequest
from ai_engine.providers.mock_provider import MockAIProvider
from models.job import Job


class BrokenResponseProvider:
    name = "broken"

    def supports(self, task: str) -> bool:
        return True

    def generate(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            success=True,
            task=request.task,
            provider=self.name,
            model=request.model or "broken-model",
            payload={"missing_required_field": True},
        )


class TimeoutProvider:
    name = "timeout"

    def supports(self, task: str) -> bool:
        return True

    def generate(self, request: AIRequest) -> AIResponse:
        raise TimeoutError("request timed out")


def test_provider_interface():
    provider = MockAIProvider(name="mock-test")
    request = AIRequest(task="job_description_understanding", payload={"job_title": "Embedded Linux Engineer"})

    assert provider.name == "mock-test"
    assert provider.supports(request.task) is True
    response = provider.generate(request)
    assert response.success is True
    assert response.payload["job_role"] == "Embedded Linux Engineer"


def test_mock_provider_returns_valid_payload():
    provider = MockAIProvider(name="mock-test")
    request = AIRequest(task="skill_extraction", payload={"description": "Embedded C, Linux, ARM Cortex-M, GPIO"})

    response = provider.generate(request)
    assert response.success is True
    assert "skills" in response.payload
    assert "linux" in [skill.lower() for skill in response.payload["skills"]]


def test_provider_selection():
    registry = AIProviderRegistry()
    provider = MockAIProvider(name="preferred")
    registry.register_provider(provider)

    selected = registry.select_provider("role_classification")
    assert selected is provider
    assert registry.get_provider("preferred") is provider


def test_missing_configuration_disables_ai():
    config = AIConfig(enabled=False)
    orchestrator = AIOrchestrator(config=config, registry=AIProviderRegistry())

    result = orchestrator.run(task="job_description_understanding", payload={"title": "Embedded Engineer"})
    assert result.disabled is True
    assert result.success is False


def test_malformed_ai_response_is_rejected():
    registry = AIProviderRegistry()
    registry.register_provider(BrokenResponseProvider())
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="broken"), registry=registry)

    result = orchestrator.run(task="job_description_understanding", payload={"title": "Embedded Engineer"})
    assert result.success is False
    assert result.error is not None


def test_timeout_and_error_handling():
    registry = AIProviderRegistry()
    registry.register_provider(TimeoutProvider())
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="timeout", timeout_seconds=1.0), registry=registry)

    result = orchestrator.run(task="role_classification", payload={"title": "Firmware Engineer"})
    assert result.success is False
    assert result.disabled is False


def test_fallback_to_deterministic_analysis():
    job = Job(
        title="Embedded Linux Engineer",
        company="Acme",
        location="Remote, India",
        experience="0-1 years",
        source="RemoteOK",
        url="https://example.com/test",
        skills=["Embedded Linux", "C", "Linux", "ARM", "GPIO"],
        posted_date="2026-08-01",
        description="Build embedded Linux firmware and Linux device drivers for ARM boards.",
    )
    registry = AIProviderRegistry()
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="missing"), registry=registry)

    result = orchestrator.safe_job_analysis(job, profile={"skills": ["C", "Linux"], "experience": "fresher"})
    assert result["role_category"] == "Embedded Linux"
    assert result["match_score"] >= 0


def test_deterministic_pipeline_with_ai_disabled():
    from ai_engine.job_filter import JobFilter

    job = Job(
        title="Embedded C Engineer",
        company="Edge Labs",
        location="Remote",
        experience="Trainee",
        source="RemoteOK",
        url="https://example.com/edge",
        skills=["C", "Embedded C", "UART", "GPIO"],
        posted_date="2026-08-02",
        description="Embedded C development for microcontrollers and UART/GPIO drivers.",
    )

    filterer = JobFilter()
    profile = {"skills": ["C", "Embedded C", "GPIO"], "experience": "fresher"}
    analysis = filterer.analyze_job_intelligence(job, profile)
    assert analysis["role_category"] in {"Embedded C", "Embedded Software"}
    assert analysis["location_match"] is True
