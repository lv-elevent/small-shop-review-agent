"""Approval Gate — safety pre-check before allowing a draft to be approved."""
from __future__ import annotations

from typing import Any


def can_approve(draft: dict[str, Any]) -> tuple[bool, str]:
    """Check whether a draft can be approved. Returns (allowed, reason).

    Only drafts with safety_status='pass' can be approved directly.
    """
    safety_status = draft.get("safety_status", "pass")
    if safety_status == "blocked":
        return False, "草稿已被安全护栏拦截，请先修改内容。"
    if safety_status == "rewrite_required":
        return False, "存在安全警告，建议按提示修改后再批准。"
    if safety_status == "pass":
        return True, ""
    return False, f"未知安全状态: {safety_status!r}"
