"""OpenAI-compatible chat adapter protocol and fail-closed boundaries."""

import json

import httpx
import pytest

from socrat.config import Settings
from socrat.tutor import gateway
from socrat.tutor.contracts import TutorOutput


@pytest.mark.parametrize(
    "failure", [None, "length", "refusal", "tool", "multiple", "json", "usage", "http"]
)
def test_chat_protocol_and_rejections(monkeypatch, failure):
    settings = Settings(
        _env_file=None,
        tutor_model_enabled=True,
        tutor_provider="openai_chat",
        tutor_model="zai-org/GLM-5.3-Flash",
        tutor_model_allowlist=["zai-org/GLM-5.3-Flash"],
        tutor_gateway_url="https://api.tokenfactory.nebius.com/v1/chat/completions",
        tutor_gateway_secret="synthetic",
        tutor_reasoning_effort="low",
        tutor_temperature=0.6,
        tutor_top_p=0.95,
    )
    choice = dict(finish_reason="stop", message=dict(content='{"synthetic": true}'))
    response = dict(choices=[choice], usage=dict(prompt_tokens=10, completion_tokens=20))
    if failure == "length":
        choice["finish_reason"] = "length"
    elif failure == "refusal":
        choice["message"]["refusal"] = "no"
    elif failure == "tool":
        choice["message"]["tool_calls"] = [{"id": "unexpected"}]
    elif failure == "multiple":
        response["choices"].append(choice)
    elif failure == "json":
        choice["message"]["content"] = "invalid"
    elif failure == "usage":
        response["usage"]["completion_tokens"] = 601

    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == settings.tutor_model
        assert body["reasoning_effort"] == "low"
        assert body["temperature"] == 0.6 and body["top_p"] == 0.95
        assert body["stream"] is False and body["max_tokens"] == 600
        assert body["store"] is False and body["n"] == 1 and body["tool_choice"] == "none"
        assert "tools" not in body
        assert body["messages"][1]["content"] == '{"reasoning": "synthetic"}'
        schema = body["response_format"]["json_schema"]
        assert schema["strict"] and schema["schema"]["additionalProperties"] is False
        assert set(schema["schema"]["required"]) == set(schema["schema"]["properties"])
        return httpx.Response(401 if failure == "http" else 200, json=response)

    client_class = httpx.AsyncClient
    monkeypatch.setattr(
        gateway.httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs),
    )
    result = gateway.generate(
        settings,
        prompt="tutor_1.0.1",
        context={"reasoning": "synthetic"},
        schema=TutorOutput.model_json_schema(),
    )
    assert (result.output is not None) == (failure is None)
    if failure == "http":
        assert result.reason == "provider_http_401"
    if failure is None:
        assert result.input_tokens == 10 and result.output_tokens == 20


@pytest.mark.parametrize("diagnostic", [False, True])
def test_uncapped_diagnostics_preserve_normal_output_limit(monkeypatch, diagnostic):
    settings = Settings(
        _env_file=None,
        tutor_model_enabled=True,
        tutor_model="synthetic",
        tutor_model_allowlist=["synthetic"],
        tutor_provider="openai_chat",
        tutor_gateway_url="https://example.test/chat/completions",
        tutor_gateway_secret="synthetic",
    )

    async def transport(settings, payload, **kwargs):
        assert ("max_tokens" not in payload) == diagnostic
        assert "temperature" not in payload and "top_p" not in payload
        assert kwargs.get("response_limit", 32000) == (1000000 if diagnostic else 32000)
        return json.dumps(
            dict(
                choices=[dict(finish_reason="stop", message=dict(content='{"complete":true}'))],
                usage=dict(prompt_tokens=10, completion_tokens=5000),
            )
        ).encode()

    monkeypatch.setattr(gateway, "transport", transport)
    result = gateway.generate(
        settings,
        prompt="tutor_1.0.1",
        context={},
        schema=TutorOutput.model_json_schema(),
        diagnostic_output_default=diagnostic,
    )
    assert (result.output is not None) == diagnostic
    if diagnostic:
        assert result.output_tokens == 5000
