"""Provider-neutral streaming gateway: Anthropic, OpenAI, or offline.

Providers only turn (system, messages) into text deltas. Policy, context and
validation live outside, so swapping providers never changes what the tutor may do.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from socrat.config import Settings


class ProviderError(RuntimeError):
    """Provider unavailable, refused or timed out. Message never echoes provider bodies."""


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    content: str


class Provider(Protocol):
    name: str

    def stream(self, system: str, turns: list[Turn], max_tokens: int) -> AsyncIterator[str]: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings):
        import anthropic

        self.settings = settings
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value() or None,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,
        )

    async def stream(self, system: str, turns: list[Turn], max_tokens: int) -> AsyncIterator[str]:
        import anthropic

        params: dict = dict(
            model=self.settings.ai_model,
            max_tokens=max_tokens,
            # Stable tutor instructions first so the prefix is cacheable across turns.
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": t.role, "content": t.content} for t in turns],
            output_config={"effort": self.settings.ai_effort},
        )
        if self.settings.ai_server_fallbacks:
            params["betas"] = ["server-side-fallback-2026-07-01"]
            params["fallbacks"] = "default"
        try:
            async with self.client.beta.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
            if final.stop_reason == "refusal":
                raise ProviderError("provider_refusal")
        except anthropic.APIConnectionError as exc:
            raise ProviderError("provider_unreachable") from exc
        except anthropic.RateLimitError as exc:
            raise ProviderError("provider_rate_limited") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"provider_http_{exc.status_code}") from exc


class OpenAIProvider:
    name = "openai"

    def __init__(self, settings: Settings):
        import openai

        self.settings = settings
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value() or None,
            base_url=settings.openai_base_url or None,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,
        )

    async def stream(self, system: str, turns: list[Turn], max_tokens: int) -> AsyncIterator[str]:
        import openai
        from openai.types.chat import ChatCompletionMessageParam

        messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system}]
        for turn in turns:
            if turn.role == "assistant":
                messages.append({"role": "assistant", "content": turn.content})
            else:
                messages.append({"role": "user", "content": turn.content})
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                stream=True,
                max_completion_tokens=max_tokens,
                messages=messages,
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.APIConnectionError as exc:
            raise ProviderError("provider_unreachable") from exc
        except openai.RateLimitError as exc:
            raise ProviderError("provider_rate_limited") from exc
        except openai.APIStatusError as exc:
            raise ProviderError(f"provider_http_{exc.status_code}") from exc


class OfflineProvider:
    """No model configured: the service substitutes curated Socratic replies."""

    name = "offline"

    async def stream(self, system: str, turns: list[Turn], max_tokens: int) -> AsyncIterator[str]:
        raise ProviderError("provider_offline")
        yield ""  # pragma: no cover - makes this an async generator


def make_provider(settings: Settings) -> Provider:
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(settings)
    if settings.ai_provider == "openai":
        return OpenAIProvider(settings)
    return OfflineProvider()
