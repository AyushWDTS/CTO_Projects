from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class CandidateAuditEntry:
    event_id: str
    headline: str
    stage: str
    decision: str
    reason: str
    source_id: str | None = None
    source_name: str | None = None
    wdts_relevance_score: float | None = None
    ai_relevance_score: float | None = None
    domain_hits: list[str] | None = None
    final_score: float | None = None
    importance_tier: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_id": self.event_id,
            "headline": self.headline,
            "stage": self.stage,
            "decision": self.decision,
            "reason": self.reason,
        }
        if self.source_id:
            payload["source_id"] = self.source_id
        if self.source_name:
            payload["source_name"] = self.source_name
        if self.wdts_relevance_score is not None:
            payload["wdts_relevance_score"] = round(self.wdts_relevance_score, 4)
        if self.ai_relevance_score is not None:
            payload["ai_relevance_score"] = round(self.ai_relevance_score, 4)
        if self.domain_hits:
            payload["domain_hits"] = self.domain_hits
        if self.final_score is not None:
            payload["final_score"] = round(self.final_score, 4)
        if self.importance_tier:
            payload["importance_tier"] = self.importance_tier
        return payload


@dataclass
class DigestSelectionAudit:
    entries: list[CandidateAuditEntry] = field(default_factory=list)

    def record_gate(
        self,
        *,
        event_id: UUID,
        headline: str,
        eligible: bool,
        reason: str,
        source_id: UUID | None = None,
        source_name: str | None = None,
        wdts_relevance_score: float | None = None,
        ai_relevance_score: float | None = None,
        domain_hits: list[str] | None = None,
        importance_tier: str | None = None,
    ) -> None:
        self.entries.append(
            CandidateAuditEntry(
                event_id=str(event_id),
                headline=headline,
                stage="relevance_gate",
                decision="eligible" if eligible else "rejected",
                reason=reason,
                source_id=str(source_id) if source_id else None,
                source_name=source_name,
                wdts_relevance_score=wdts_relevance_score,
                ai_relevance_score=ai_relevance_score,
                domain_hits=domain_hits,
                importance_tier=importance_tier,
            )
        )

    def record_ranking(
        self,
        *,
        event_id: UUID,
        headline: str,
        selected: bool,
        reason: str,
        final_score: float | None = None,
        importance_tier: str | None = None,
        source_id: UUID | None = None,
        source_name: str | None = None,
    ) -> None:
        self.entries.append(
            CandidateAuditEntry(
                event_id=str(event_id),
                headline=headline,
                stage="ranking",
                decision="selected" if selected else "not_selected",
                reason=reason,
                source_id=str(source_id) if source_id else None,
                source_name=source_name,
                final_score=final_score,
                importance_tier=importance_tier,
            )
        )

    def summary(self) -> dict[str, Any]:
        gate_rejected = sum(
            1
            for entry in self.entries
            if entry.stage == "relevance_gate" and entry.decision == "rejected"
        )
        gate_eligible = sum(
            1
            for entry in self.entries
            if entry.stage == "relevance_gate" and entry.decision == "eligible"
        )
        ranking_selected = sum(
            1 for entry in self.entries if entry.stage == "ranking" and entry.decision == "selected"
        )
        reject_by_reason: dict[str, int] = {}
        reject_by_source: dict[str, int] = {}
        for entry in self.entries:
            if entry.stage == "relevance_gate" and entry.decision == "rejected":
                reject_by_reason[entry.reason] = reject_by_reason.get(entry.reason, 0) + 1
                if entry.source_id:
                    reject_by_source[entry.source_id] = reject_by_source.get(entry.source_id, 0) + 1
        return {
            "gate_eligible": gate_eligible,
            "gate_rejected": gate_rejected,
            "ranking_selected": ranking_selected,
            "reject_by_reason": reject_by_reason,
            "reject_by_source": reject_by_source,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "entries": [entry.to_dict() for entry in self.entries],
        }
