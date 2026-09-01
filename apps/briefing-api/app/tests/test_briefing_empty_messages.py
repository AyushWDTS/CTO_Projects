from app.data.briefing_empty_messages import empty_section_message
from app.data.briefing_sections import BriefingSection


def test_empty_section_message_uses_coverage_status() -> None:
    ai_message = empty_section_message(BriefingSection.AI_ML_CV.value)
    assert "partially covered" in ai_message
    assert "Academic CV" in ai_message

    semiconductor_message = empty_section_message(BriefingSection.SEMICONDUCTORS.value)
    assert "partially covered" in semiconductor_message

    smart_table_message = empty_section_message(BriefingSection.SMART_TABLES.value)
    assert "partially covered" in smart_table_message
