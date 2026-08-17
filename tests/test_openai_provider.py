import pytest

from ai_engine.ai_orchestrator import AIConfig, AIOrchestrator, AIProviderRegistry
from ai_engine.ai_types import AIRequest
from ai_engine.providers.openai_compatible_provider import OpenAICompatibleProvider


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_openai_provider_disabled_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAICompatibleProvider(api_key="", base_url="https://example.test/v1")
    assert provider.enabled is False
    assert provider.supports("role_classification") is False


def test_openai_provider_uses_configured_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = OpenAICompatibleProvider.from_settings()
    assert provider is not None
    assert provider.enabled is True
    assert provider.supports("role_classification") is True


def test_openai_provider_validates_json_response(monkeypatch):
    provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://example.test/v1")

    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": '{"result": {"role": "Embedded Engineer"}, "status": "ok"}'
                }
            }]
        })

    monkeypatch.setattr("ai_engine.providers.openai_compatible_provider.requests.post", fake_post)
    response = provider.generate(AIRequest(task="role_classification", payload={"title": "Embedded Engineer"}))
    assert response.success is True
    assert response.payload["result"]["role"] == "Embedded Engineer"


def test_openai_provider_handles_network_failure(monkeypatch):
    provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://example.test/v1")

    def fake_post(url, headers=None, json=None, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr("ai_engine.providers.openai_compatible_provider.requests.post", fake_post)
    response = provider.generate(AIRequest(task="skill_extraction", payload={"description": "C, Linux"}))
    assert response.success is False
    assert "timed out" in response.error.lower()


def test_orchestrator_uses_openai_provider_when_enabled(monkeypatch):
    registry = AIProviderRegistry()
    provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://example.test/v1")
    registry.register_provider(provider)

    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": '{"result": {"role": "Embedded Linux Engineer"}, "status": "ok"}'
                }
            }]
        })

    monkeypatch.setattr("ai_engine.providers.openai_compatible_provider.requests.post", fake_post)
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="openai", required_fields=["result", "status"]), registry=registry)
    result = orchestrator.run(task="role_classification", payload={"title": "Embedded Linux Engineer"})
    assert result.success is True
    assert result.payload["result"]["role"] == "Embedded Linux Engineer"
