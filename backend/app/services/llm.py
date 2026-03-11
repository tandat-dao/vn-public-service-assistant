"""LLM service — wraps the Anthropic client for agent use."""


class LLMService:
    """Anthropic Claude client wrapper."""

    async def complete(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    async def stream(self, prompt: str, **kwargs):
        raise NotImplementedError
