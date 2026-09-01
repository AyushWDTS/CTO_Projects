from app.services.briefing_text_service import (
    distinct_summary,
    limit_sentences,
    resolve_suggested_action,
    summaries_match,
)


def test_limit_sentences_caps_at_max() -> None:
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    assert limit_sentences(text, 2) == "First sentence. Second sentence."
    assert limit_sentences(text, 3) == "First sentence. Second sentence. Third sentence."


def test_limit_sentences_preserves_short_text() -> None:
    text = "Only one sentence"
    assert limit_sentences(text, 2) == "Only one sentence"


def test_limit_sentences_handles_empty() -> None:
    assert limit_sentences("", 2) == ""
    assert limit_sentences(None, 2) == ""


def test_summaries_match_ignores_case_and_punctuation() -> None:
    assert summaries_match("Casino rule changes.", "casino rule changes")
    assert not summaries_match("Casino rule changes.", "Operators may need to adapt.")


def test_distinct_summary_returns_empty_when_duplicate_without_fallback() -> None:
    headline = "Casino regulation changed."
    assert distinct_summary(headline, headline) == ""


def test_distinct_summary_uses_fallback_when_duplicate() -> None:
    headline = "Casino regulation changed."
    fallback = "Operators may need to update compliance programs."
    assert distinct_summary(headline, headline, fallback=fallback) == fallback


def test_distinct_summary_limits_non_duplicate_to_two_sentences() -> None:
    summary = "First point. Second point. Third point."
    assert (
        distinct_summary("Different headline.", summary)
        == "First point. Second point."
    )


def test_resolve_suggested_action_prefers_explicit_action() -> None:
    assert (
        resolve_suggested_action(
            "Review supplier exposure with operations.",
            "No action",
        )
        == "Review supplier exposure with operations."
    )


def test_resolve_suggested_action_uses_action_bucket_when_actionable() -> None:
    assert resolve_suggested_action(None, "Monitor") == "Monitor"


def test_resolve_suggested_action_hides_no_action() -> None:
    assert resolve_suggested_action(None, "No action") == ""
    assert resolve_suggested_action("No action", "Monitor") == "Monitor"

