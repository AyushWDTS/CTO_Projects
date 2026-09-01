import httpx
import pytest

from app.core.config import Settings
from app.services.ai_provider import (
    AIProviderError,
    BedrockProvider,
    GeminiProvider,
    MissingAIAPIKeyError,
    OpenAICompatibleProvider,
    get_ai_provider,
)


def test_provider_requires_api_key() -> None:
    provider = OpenAICompatibleProvider(Settings(AI_API_KEY=""))

    with pytest.raises(MissingAIAPIKeyError):
        provider.analyze("prompt")


def test_provider_surfaces_safe_http_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 429
        text = '{"error":{"message":"You exceeded your current quota","type":"insufficient_quota"}}'

        def raise_for_status(self) -> None:
            request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            response = httpx.Response(self.status_code, text=self.text, request=request)
            raise httpx.HTTPStatusError("too many requests", request=request, response=response)

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr("app.services.ai_provider.httpx.Client", FakeClient)
    monkeypatch.setattr("app.services.ai_provider.time.sleep", lambda _: None)
    provider = OpenAICompatibleProvider(
        Settings(AI_API_KEY="key", AI_MAX_RETRIES=1, AI_MODEL="gpt-4.1-mini", AI_TIMEOUT_SECONDS=30)
    )

    with pytest.raises(AIProviderError) as error:
        provider.analyze("prompt")

    message = str(error.value)
    assert "ai_http_429" in message
    assert "insufficient_quota" in message
    assert "key" not in message


def test_get_ai_provider_selects_gemini() -> None:
    provider = get_ai_provider(Settings(AI_PROVIDER="gemini"))

    assert isinstance(provider, GeminiProvider)


def test_get_ai_provider_selects_bedrock() -> None:
    provider = get_ai_provider(Settings(AI_PROVIDER="bedrock"))

    assert isinstance(provider, BedrockProvider)


def test_bedrock_provider_parses_converse_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def converse(self, **kwargs: object) -> dict:
            assert kwargs["modelId"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
            return {
                "modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": (
                                    '```json\n{"summary":"Longer context.","short_summary":"Headline.",'
                                    '"why_it_matters":"Relevant.","key_points":["Point"]}\n```'
                                ),
                            }
                        ]
                    }
                },
                "usage": {
                    "inputTokens": 100,
                    "outputTokens": 50,
                    "totalTokens": 150,
                },
            }

    monkeypatch.setattr(
        "boto3.client",
        lambda **kwargs: FakeClient(),
    )

    class FakeSession:
        def client(self, service_name: str) -> FakeClient:
            assert service_name == "bedrock-runtime"
            return FakeClient()

    monkeypatch.setattr("boto3.Session", lambda **kwargs: FakeSession())
    provider = BedrockProvider(
        Settings(
            AI_PROVIDER="bedrock",
            BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0",
            AWS_REGION="us-east-1",
            AWS_PROFILE="",
        )
    )

    response = provider.analyze("prompt")

    assert "summary" in response.content
    assert response.model_name == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    assert response.usage.prompt_tokens == 100
    assert response.usage.completion_tokens == 50
    assert response.usage.total_tokens == 150


def test_bedrock_provider_parses_tool_use_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def converse(self, **kwargs: object) -> dict:
            return {
                "modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "name": "emit_event_analysis",
                                    "input": {
                                        "summary": "Longer context.",
                                        "short_summary": "Headline.",
                                        "why_it_matters": "Relevant.",
                                        "key_points": ["Point"],
                                    },
                                }
                            }
                        ]
                    }
                },
                "usage": {
                    "inputTokens": 10,
                    "outputTokens": 5,
                    "totalTokens": 15,
                },
            }

    monkeypatch.setattr("boto3.client", lambda **kwargs: FakeClient())

    class FakeSession:
        def client(self, service_name: str) -> FakeClient:
            return FakeClient()

    monkeypatch.setattr("boto3.Session", lambda **kwargs: FakeSession())
    provider = BedrockProvider(
        Settings(
            AI_PROVIDER="bedrock",
            BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0",
            AWS_REGION="us-east-1",
            AWS_PROFILE="",
        )
    )

    response = provider.analyze("prompt")

    assert '"summary": "Longer context."' in response.content


def test_gemini_provider_requires_api_key() -> None:
    provider = GeminiProvider(Settings(AI_PROVIDER="gemini", GEMINI_API_KEY=""))

    with pytest.raises(MissingAIAPIKeyError):
        provider.analyze("prompt")


def test_gemini_provider_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"summary":"ok","key_points":[]}',
                                }
                            ]
                        }
                    }
                ],
                "modelVersion": "gemini-2.5-flash",
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "totalTokenCount": 15,
                },
            }

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, *args: object, **kwargs: object) -> FakeResponse:
            assert url.endswith("/models/gemini-2.5-flash:generateContent")
            headers = kwargs["headers"]
            assert headers["x-goog-api-key"] == "gemini-key"
            assert "Authorization" not in headers
            return FakeResponse()

    monkeypatch.setattr("app.services.ai_provider.httpx.Client", FakeClient)
    provider = GeminiProvider(
        Settings(
            AI_PROVIDER="gemini",
            GEMINI_API_KEY="gemini-key",
            GEMINI_MODEL="gemini-2.5-flash",
            AI_TIMEOUT_SECONDS=30,
        )
    )

    response = provider.analyze("prompt")

    assert response.content == '{"summary":"ok","key_points":[]}'
    assert response.model_name == "gemini-2.5-flash"
    assert response.usage.prompt_tokens == 10
    assert response.usage.completion_tokens == 5
    assert response.usage.total_tokens == 15


def test_gemini_provider_surfaces_safe_http_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 400
        text = '{"error":{"message":"API key not valid","status":"INVALID_ARGUMENT"}}'

        def raise_for_status(self) -> None:
            request = httpx.Request(
                "POST",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            )
            response = httpx.Response(self.status_code, text=self.text, request=request)
            raise httpx.HTTPStatusError("bad request", request=request, response=response)

    class FakeClient:
        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr("app.services.ai_provider.httpx.Client", FakeClient)
    provider = GeminiProvider(
        Settings(AI_PROVIDER="gemini", GEMINI_API_KEY="gemini-key", AI_TIMEOUT_SECONDS=30)
    )

    with pytest.raises(AIProviderError) as error:
        provider.analyze("prompt")

    message = str(error.value)
    assert "ai_http_400" in message
    assert "API key not valid" in message
    assert "gemini-key" not in message
