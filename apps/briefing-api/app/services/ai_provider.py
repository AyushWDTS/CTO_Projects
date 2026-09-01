import json
import time
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings
from app.data.bedrock_analysis_schema import bedrock_event_analysis_input_schema
from app.schemas.ai_provider import AIProviderResponse, AIProviderUsage
from app.services.ai_response_parser import extract_json_object, preview_model_content


class AIProviderError(Exception):
    pass


class MissingAIAPIKeyError(AIProviderError):
    pass


class AIProviderConfigError(AIProviderError):
    pass


MAX_PROVIDER_ERROR_BODY_LENGTH = 500
BEDROCK_ANALYSIS_TOOL_NAME = "emit_event_analysis"


class EventAnalysisProvider(Protocol):
    def analyze(self, prompt: str) -> AIProviderResponse:
        pass


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(self, prompt: str) -> AIProviderResponse:
        if not self.settings.AI_API_KEY:
            raise MissingAIAPIKeyError("missing_ai_api_key")

        payload = {
            "model": self.settings.AI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You return JSON only for business news intelligence analysis.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.AI_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.AI_BASE_URL.rstrip('/')}/chat/completions"
        last_error_message: str | None = None

        for attempt in range(self.settings.AI_MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=self.settings.AI_TIMEOUT_SECONDS) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    body = response.json()
                content = body["choices"][0]["message"]["content"]
                usage = body.get("usage") or {}
                return AIProviderResponse(
                    content=content if isinstance(content, str) else json.dumps(content),
                    model_name=body.get("model") or self.settings.AI_MODEL,
                    usage=AIProviderUsage(
                        prompt_tokens=usage.get("prompt_tokens") or 0,
                        completion_tokens=usage.get("completion_tokens") or 0,
                        total_tokens=usage.get("total_tokens") or 0,
                    ),
                )
            except httpx.HTTPStatusError as exc:
                last_error_message = _format_ai_http_error(exc)
                if exc.response.status_code < 500 and exc.response.status_code != 429:
                    break
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))
            except httpx.HTTPError as exc:
                last_error_message = str(exc)
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))
            except (KeyError, TypeError, ValueError) as exc:
                last_error_message = f"invalid_ai_response: {exc}"
                break
            except Exception as exc:
                last_error_message = str(exc)
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))

        raise AIProviderError(last_error_message or "ai_provider_error")


class GeminiProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(self, prompt: str) -> AIProviderResponse:
        if not self.settings.GEMINI_API_KEY.strip():
            raise MissingAIAPIKeyError("missing_gemini_api_key")

        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": "You return JSON only for business news intelligence analysis.",
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.settings.GEMINI_API_KEY,
        }
        url = (
            f"{self.settings.GEMINI_BASE_URL.rstrip('/')}"
            f"/models/{self.settings.GEMINI_MODEL}:generateContent"
        )
        last_error_message: str | None = None

        for attempt in range(self.settings.AI_MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=self.settings.AI_TIMEOUT_SECONDS) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    body = response.json()
                content = _extract_gemini_text(body)
                usage = body.get("usageMetadata") or {}
                return AIProviderResponse(
                    content=content,
                    model_name=body.get("modelVersion") or self.settings.GEMINI_MODEL,
                    usage=AIProviderUsage(
                        prompt_tokens=usage.get("promptTokenCount") or 0,
                        completion_tokens=usage.get("candidatesTokenCount") or 0,
                        total_tokens=usage.get("totalTokenCount") or 0,
                    ),
                )
            except httpx.HTTPStatusError as exc:
                last_error_message = _format_ai_http_error(exc)
                if exc.response.status_code < 500 and exc.response.status_code != 429:
                    break
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))
            except httpx.HTTPError as exc:
                last_error_message = str(exc)
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))
            except (KeyError, TypeError, ValueError) as exc:
                last_error_message = f"invalid_gemini_response: {exc}"
                break
            except Exception as exc:
                last_error_message = str(exc)
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))

        raise AIProviderError(last_error_message or "gemini_provider_error")


class BedrockProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(self, prompt: str) -> AIProviderResponse:
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound
        except ImportError as exc:
            raise AIProviderConfigError("boto3 is required for AI_PROVIDER=bedrock") from exc

        region = (self.settings.AWS_REGION or "").strip() or None
        profile = (self.settings.AWS_PROFILE or "").strip() or None
        model_id = (self.settings.BEDROCK_MODEL_ID or self.settings.AI_MODEL).strip()
        if not model_id:
            raise AIProviderConfigError("missing_bedrock_model_id")

        try:
            from botocore.config import Config as BotocoreConfig

            timeout_seconds = max(5, self.settings.AI_TIMEOUT_SECONDS)
            botocore_cfg = BotocoreConfig(
                connect_timeout=10,
                read_timeout=timeout_seconds,
                retries={"max_attempts": 0},
            )

            if profile:
                session = boto3.Session(profile_name=profile, region_name=region)
                client = session.client("bedrock-runtime", config=botocore_cfg)
            else:
                client_kwargs: dict[str, str] = {"service_name": "bedrock-runtime"}
                if region:
                    client_kwargs["region_name"] = region
                client = boto3.client(**client_kwargs, config=botocore_cfg)
        except ProfileNotFound as exc:
            raise AIProviderConfigError(
                "aws_profile_not_found: mount ~/.aws into the container or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY"
            ) from exc
        except NoCredentialsError as exc:
            raise MissingAIAPIKeyError("missing_aws_credentials") from exc

        payload = {
            "modelId": model_id,
            "system": [
                {
                    "text": (
                        "You return JSON only for WDTS business news intelligence analysis. "
                        "Populate suggested_action with a concrete next step for product, "
                        "engineering, or go-to-market teams when action_bucket is Monitor, "
                        "Discuss with team, or Immediate attention. "
                        "Set action_bucket to No action only when no follow-up is warranted."
                    ),
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            "inferenceConfig": {
                "temperature": 0.1,
                "maxTokens": 4096,
            },
            "toolConfig": _bedrock_analysis_tool_config(),
        }
        last_error_message: str | None = None
        use_tool_config = True

        for attempt in range(self.settings.AI_MAX_RETRIES + 1):
            try:
                request_payload = payload if use_tool_config else _without_tool_config(payload)
                response = client.converse(**request_payload)
                content = _normalize_bedrock_model_content(_extract_bedrock_text(response))
                usage = response.get("usage") or {}
                return AIProviderResponse(
                    content=content,
                    model_name=response.get("modelId") or model_id,
                    usage=AIProviderUsage(
                        prompt_tokens=usage.get("inputTokens") or 0,
                        completion_tokens=usage.get("outputTokens") or 0,
                        total_tokens=usage.get("totalTokens") or 0,
                    ),
                )
            except ClientError as exc:
                last_error_message = _format_bedrock_client_error(exc)
                error_code = exc.response.get("Error", {}).get("Code", "")
                if use_tool_config and _bedrock_tool_config_unsupported(error_code):
                    use_tool_config = False
                    continue
                if error_code not in {
                    "ThrottlingException",
                    "ServiceUnavailableException",
                    "ModelTimeoutException",
                }:
                    break
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))
            except (BotoCoreError, KeyError, TypeError, ValueError) as exc:
                last_error_message = f"invalid_bedrock_response: {exc}"
                if use_tool_config:
                    use_tool_config = False
                    continue
                break
            except Exception as exc:
                last_error_message = str(exc)
                if attempt < self.settings.AI_MAX_RETRIES:
                    time.sleep(0.2 * (attempt + 1))

        raise AIProviderError(last_error_message or "bedrock_provider_error")


def get_ai_provider(settings: Settings | None = None) -> EventAnalysisProvider:
    settings = settings or get_settings()
    provider = settings.AI_PROVIDER.strip().lower()
    if provider in {"openai", "openai_compatible"}:
        return OpenAICompatibleProvider(settings)
    if provider in {"gemini", "google_gemini"}:
        return GeminiProvider(settings)
    if provider == "bedrock":
        return BedrockProvider(settings)
    raise AIProviderConfigError(f"Unsupported AI provider: {settings.AI_PROVIDER}")


def _format_ai_http_error(exc: httpx.HTTPStatusError) -> str:
    status_code = exc.response.status_code
    body = exc.response.text.strip()
    if len(body) > MAX_PROVIDER_ERROR_BODY_LENGTH:
        body = body[:MAX_PROVIDER_ERROR_BODY_LENGTH] + "..."
    if body:
        return f"ai_http_{status_code}: {body}"
    return f"ai_http_{status_code}"


def _extract_gemini_text(body: dict) -> str:
    candidates = body["candidates"]
    if not candidates:
        raise ValueError("Gemini response did not include candidates")
    parts = candidates[0]["content"]["parts"]
    text = "\n".join(str(part["text"]) for part in parts if part.get("text"))
    if not text.strip():
        raise ValueError("Gemini response did not include text")
    return text


def _extract_bedrock_text(body: dict) -> str:
    message = body["output"]["message"]
    parts = message.get("content") or []
    text_parts: list[str] = []
    for part in parts:
        if part.get("text"):
            text_parts.append(str(part["text"]))
        tool_use = part.get("toolUse")
        if isinstance(tool_use, dict) and tool_use.get("input") is not None:
            tool_input = tool_use["input"]
            if isinstance(tool_input, dict):
                text_parts.append(json.dumps(tool_input))
            else:
                text_parts.append(str(tool_input))
    text = "\n".join(text_parts)
    if not text.strip():
        stop_reason = body.get("stopReason")
        raise ValueError(
            "Bedrock response did not include text"
            + (f" (stopReason={stop_reason})" if stop_reason else "")
        )
    return text


def _normalize_bedrock_model_content(content: str) -> str:
    normalized = extract_json_object(content)
    if not normalized.strip():
        preview = preview_model_content(content)
        raise ValueError(f"Bedrock response did not include JSON text (preview={preview!r})")
    return normalized


def _bedrock_analysis_tool_config() -> dict[str, Any]:
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": BEDROCK_ANALYSIS_TOOL_NAME,
                    "description": "Return structured event analysis as JSON.",
                    "inputSchema": {
                        "json": bedrock_event_analysis_input_schema(),
                    },
                }
            }
        ],
        "toolChoice": {"tool": {"name": BEDROCK_ANALYSIS_TOOL_NAME}},
    }


def _without_tool_config(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "toolConfig"}


def _bedrock_tool_config_unsupported(error_code: str) -> bool:
    return error_code in {
        "ValidationException",
        "AccessDeniedException",
        "ResourceNotFoundException",
    }


def _format_bedrock_client_error(exc: Exception) -> str:
    response = getattr(exc, "response", None) or {}
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    code = error.get("Code") or "ClientError"
    message = error.get("Message") or str(exc)
    if len(message) > MAX_PROVIDER_ERROR_BODY_LENGTH:
        message = message[:MAX_PROVIDER_ERROR_BODY_LENGTH] + "..."
    return f"bedrock_{code}: {message}"
