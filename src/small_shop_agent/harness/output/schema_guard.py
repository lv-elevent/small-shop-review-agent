"""Schema Guard — validates LLM outputs against Pydantic models without raising."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from small_shop_agent.utils.logger import log_step


@dataclass
class SchemaGuardResult:
    """Result of schema validation. Never raises — check .ok field."""
    ok: bool = False
    validated: list[BaseModel] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    total_input: int = 0
    total_valid: int = 0
    total_invalid: int = 0


def _validate_one(model: type[BaseModel], item: dict[str, Any]) -> BaseModel:
    """Validate a single dict against a Pydantic model. Raises ValidationError."""
    if hasattr(model, "model_validate"):
        return model.model_validate(item)
    return model.parse_obj(item)  # pydantic v1 fallback


def validate_output(
    data: list[dict[str, Any]] | dict[str, Any],
    model: type[BaseModel],
    *,
    many: bool = True,
    batch_id: str = "",
) -> SchemaGuardResult:
    """Validate LLM output against a Pydantic model.

    Args:
        data: List of dicts (many=True) or a single dict (many=False).
        model: Pydantic BaseModel subclass to validate against.
        many: If True, data is a list; each item validated individually.
        batch_id: Optional batch ID for structured logging.

    Returns:
        SchemaGuardResult — check .ok; valid items in .validated even on partial failure.
    """
    items: list[dict[str, Any]] = data if many else [data]
    result = SchemaGuardResult(total_input=len(items))

    log_step("schema_guard_start", batch_id or "unknown", item_count=len(items))

    for i, item in enumerate(items):
        try:
            instance = _validate_one(model, item)
            result.validated.append(instance)
            result.total_valid += 1
        except ValidationError as exc:
            result.total_invalid += 1
            result.errors.append({
                "index": i,
                "input": item,
                "errors": exc.errors(),
            })

    result.ok = result.total_invalid == 0 and result.total_valid > 0
    log_step("schema_guard_done", batch_id or "unknown",
            total_valid=result.total_valid, total_invalid=result.total_invalid, ok=result.ok)
    return result
