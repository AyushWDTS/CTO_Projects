from uuid import uuid4

from app.services.digest_selection_audit import DigestSelectionAudit


def test_selection_audit_records_gate_and_ranking_summary() -> None:
    audit = DigestSelectionAudit()
    event_id = uuid4()
    source_id = uuid4()
    audit.record_gate(
        event_id=event_id,
        headline="Casino regulator update",
        eligible=False,
        reason="finance_noise",
        source_id=source_id,
        source_name="Test Source",
        wdts_relevance_score=0.1,
        importance_tier="monitor",
    )
    audit.record_gate(
        event_id=uuid4(),
        headline="Smart table RFID rollout",
        eligible=True,
        reason="passed_wdts_gate",
        wdts_relevance_score=0.72,
        importance_tier="important",
    )
    audit.record_ranking(
        event_id=uuid4(),
        headline="Smart table RFID rollout",
        selected=True,
        reason="within_limit",
        final_score=0.81,
        importance_tier="important",
    )

    payload = audit.to_dict()
    assert payload["summary"]["gate_rejected"] == 1
    assert payload["summary"]["gate_eligible"] == 1
    assert payload["summary"]["ranking_selected"] == 1
    assert payload["summary"]["reject_by_reason"]["finance_noise"] == 1
    assert payload["summary"]["reject_by_source"][str(source_id)] == 1
    assert len(payload["entries"]) == 3
