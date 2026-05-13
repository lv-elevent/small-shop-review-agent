"""Evidence Guard — validates insight evidence binding without LLM or DB calls."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from small_shop_agent.core.config import MIN_EVIDENCE_COUNT
from small_shop_agent.utils.logger import log_step


# ── Per-issue result ───────────────────────────────────────────────────

@dataclass
class EvidenceGuardIssueResult:
    """Result for a single insight's evidence check."""
    issue_id: str | None = None
    topic: str = ""
    status: str = "invalid"       # sufficient | evidence_insufficient | invalid
    evidence_review_ids: list[str] = field(default_factory=list)
    missing_review_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class EvidenceGuardResult:
    """Aggregate result of evidence validation across all insights."""
    ok: bool = False
    issues: list[EvidenceGuardIssueResult] = field(default_factory=list)
    valid_issues: list[dict[str, Any]] = field(default_factory=list)
    rejected_issues: list[dict[str, Any]] = field(default_factory=list)


# ── Input adaptation ───────────────────────────────────────────────────

def _extract_issue_id(insight: dict[str, Any]) -> str | None:
    for key in ("id", "insight_id", "issue_id", "rank"):
        val = insight.get(key)
        if val is not None:
            return str(val)
    return None


def _extract_review_ids(insight: dict[str, Any]) -> list[str]:
    """Auto-detect evidence field and return list of review_id strings."""
    # Direct list-of-strings fields
    for key in ("evidence_review_ids", "review_ids", "evidence_ids"):
        val = insight.get(key)
        if isinstance(val, list) and val and all(isinstance(x, str) for x in val):
            return val

    # Nested evidence list of dicts (each with 'review_id')
    evidence = insight.get("evidence")
    if isinstance(evidence, list):
        ids: list[str] = []
        for e in evidence:
            if isinstance(e, dict) and "review_id" in e:
                ids.append(str(e["review_id"]))
        return ids

    return []


def _build_review_id_set(reviews: list[dict[str, Any]]) -> set[str]:
    return {str(r.get("review_id", "")) for r in reviews if r.get("review_id")}


# ── Core function ──────────────────────────────────────────────────────

def validate_insight_evidence(
    insights: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    *,
    min_evidence_count: int = MIN_EVIDENCE_COUNT,
    batch_id: str = "",
) -> EvidenceGuardResult:
    """Validate that every insight has sufficient evidence bound to real reviews.

    Args:
        insights: List of insight dicts (any evidence field format).
        reviews: List of review dicts (must have review_id).
        min_evidence_count: Minimum valid evidence review_ids per insight (default 2).
        batch_id: Optional batch ID for structured logging.

    Returns:
        EvidenceGuardResult with ok=True only when all insights are sufficient.
    """
    valid_review_ids = _build_review_id_set(reviews)
    result = EvidenceGuardResult()
    bid = batch_id or "unknown"

    for insight in insights:
        topic = str(insight.get("topic", insight.get("issue_name", "")))
        issue_id = _extract_issue_id(insight)
        raw_ids = _extract_review_ids(insight)

        pres_ids: list[str] = []
        miss_ids: list[str] = []
        reasons: list[str] = []

        for rid in raw_ids:
            if rid in valid_review_ids:
                pres_ids.append(rid)
            else:
                miss_ids.append(rid)

        if miss_ids:
            reasons.append(f"证据引用了不存在的 review_id: {miss_ids}")

        # Determine status
        if not raw_ids:
            status = "invalid"
            reasons.insert(0, "洞察未关联任何证据（缺少 evidence 相关字段）")
        elif not pres_ids:
            status = "invalid"
            if not reasons:
                reasons.insert(0, "所有证据的 review_id 均不存在于当前批次评论中")
            else:
                reasons.insert(0, "所有证据的 review_id 均不存在于当前批次评论中")
        elif len(pres_ids) < min_evidence_count:
            status = "evidence_insufficient"
            reasons.insert(0, f"有效证据不足：需要至少 {min_evidence_count} 条，实际 {len(pres_ids)} 条")
        else:
            status = "sufficient"
            reasons.insert(0, f"证据充足：{len(pres_ids)} 条有效证据")

        log_step("evidence_guard_check", bid, issue_id=issue_id, topic=topic,
                evidence_status=status, evidence_count=len(pres_ids),
                missing_count=len(miss_ids))
        issue_result = EvidenceGuardIssueResult(
            issue_id=issue_id,
            topic=topic,
            status=status,
            evidence_review_ids=pres_ids,
            missing_review_ids=miss_ids,
            reasons=reasons,
        )
        result.issues.append(issue_result)

        # Build normalized output dict
        normalized = dict(insight)
        normalized["evidence_review_ids"] = pres_ids
        normalized["evidence_status"] = status
        # Drop old key variants so only normalized fields remain
        for old_key in ("review_ids", "evidence_ids", "evidence"):
            normalized.pop(old_key, None)

        if status == "sufficient":
            result.valid_issues.append(normalized)
        else:
            result.rejected_issues.append(normalized)

    result.ok = len(result.rejected_issues) == 0 and len(result.valid_issues) > 0
    return result
