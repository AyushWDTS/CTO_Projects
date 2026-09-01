import json
import re
from typing import Any

MAX_RAW_CONTENT_PREVIEW = 500


class InvalidModelJsonError(ValueError):
    def __init__(self, message: str, *, raw_content: str | None = None) -> None:
        super().__init__(message)
        self.raw_content = raw_content


def preview_model_content(content: str, limit: int = MAX_RAW_CONTENT_PREVIEW) -> str:
    text = content.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def strip_json_markdown_fences(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_json_object(content: str) -> str:
    text = strip_json_markdown_fences(content)
    if not text:
        return text
    if text[0] in "{[":
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def parse_model_json(content: str) -> dict[str, Any]:
    normalized = extract_json_object(content)
    if not normalized.strip():
        raise InvalidModelJsonError(
            "empty_model_json",
            raw_content=preview_model_content(content),
        )
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise InvalidModelJsonError(
            f"json_decode_error: {exc}",
            raw_content=preview_model_content(content),
        ) from exc
    if not isinstance(parsed, dict):
        raise InvalidModelJsonError(
            f"expected_json_object got {type(parsed).__name__}",
            raw_content=preview_model_content(content),
        )
    return parsed
