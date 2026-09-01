from app.data.bedrock_analysis_schema import (
    bedrock_event_analysis_input_schema,
    is_actionable_suggestion,
)


def test_bedrock_schema_includes_action_fields() -> None:
    schema = bedrock_event_analysis_input_schema()
    properties = schema["properties"]
    required = set(schema["required"])
    assert "suggested_action" in properties
    assert "action_bucket" in properties
    assert "relevance_score" in properties
    assert "urgency_score" in properties
    assert "signal_type" in properties
    assert "why_it_matters_to_wdts" in required
    assert "briefing_section" in required


def test_is_actionable_suggestion_filters_no_action() -> None:
    assert is_actionable_suggestion("Monitor")
    assert not is_actionable_suggestion("No action")
    assert not is_actionable_suggestion("")
