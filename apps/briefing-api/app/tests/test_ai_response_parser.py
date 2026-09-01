import pytest

from app.services.ai_response_parser import (
    InvalidModelJsonError,
    extract_json_object,
    parse_model_json,
    strip_json_markdown_fences,
)


def test_strip_json_markdown_fences() -> None:
    content = '```json\n{"summary":"ok"}\n```'
    assert strip_json_markdown_fences(content) == '{"summary":"ok"}'


def test_extract_json_object_from_prose_prefix() -> None:
    content = 'Here is the analysis:\n{"summary":"ok","short_summary":"headline"}'
    assert extract_json_object(content) == '{"summary":"ok","short_summary":"headline"}'


def test_parse_model_json_accepts_fenced_json() -> None:
    parsed = parse_model_json('```json\n{"summary":"ok","short_summary":"headline"}\n```')
    assert parsed["summary"] == "ok"


def test_parse_model_json_rejects_empty_content() -> None:
    with pytest.raises(InvalidModelJsonError) as error:
        parse_model_json("   ")

    assert error.value.raw_content == ""


def test_parse_model_json_rejects_non_object_json() -> None:
    with pytest.raises(InvalidModelJsonError):
        parse_model_json("[]")
