from ai_engine.ai_orchestrator import AIConfig, AIOrchestrator, AIProviderRegistry
from ai_engine.providers.mock_provider import MockAIProvider


def build_default_ai_registry():
    """Create the default AI registry for optional provider-backed analysis.

    The real provider is only added when an API key is configured. This keeps the
    deterministic pipeline working normally if AI is not enabled.
    """
    from ai_engine.providers.openai_compatible_provider import OpenAICompatibleProvider

    registry = AIProviderRegistry()
    provider = OpenAICompatibleProvider.from_settings()
    if provider is not None and provider.enabled:
        registry.register_provider(provider)

    # Keep the mock provider available for tests and offline development.
    registry.register_provider(MockAIProvider(name="mock"))
    return registry


__all__ = ["AIConfig", "AIOrchestrator", "AIProviderRegistry", "build_default_ai_registry"]
