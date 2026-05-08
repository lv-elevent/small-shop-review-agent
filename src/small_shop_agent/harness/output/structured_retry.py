"""Structured Retry — wraps a call_fn with schema validation and retry logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from small_shop_agent.harness.output.schema_guard import validate_output


@dataclass
class StructuredRetryResult:
    """Result of a schema-retry loop. Never raises — check .ok field."""
    ok: bool = False
    data: Any | None = None
    attempts: int = 0
    used_fallback: bool = False
    errors: list[str] = field(default_factory=list)
    schema_name: str = ""


def _fmt_schema_errors(guard_result: Any) -> list[str]:
    """Convert SchemaGuardResult errors to human-readable strings."""
    out: list[str] = []
    for err in guard_result.errors:
        idx = err["index"]
        details = err["errors"]
        out.append(f"index {idx}: {details}")
    return out


def run_with_schema_retry(
    call_fn: Callable[..., Any],
    schema_cls: type[Any],
    *,
    many: bool = False,
    max_retries: int = 1,
    fallback_fn: Callable[[], Any] | None = None,
) -> StructuredRetryResult:
    """Call call_fn, validate with schema, retry on failure, fallback if exhausted.

    Args:
        call_fn: Called as call_fn(attempt=N) where N is 1-indexed.
        schema_cls: Pydantic BaseModel to validate against.
        many: Passed through to validate_output.
        max_retries: Extra attempts after the first (default 1 → 2 total calls).
        fallback_fn: Called with no args when all retries fail; output also validated.

    Returns:
        StructuredRetryResult — check .ok; .data holds validated model(s).
    """
    errors: list[str] = []

    for attempt in range(1, max_retries + 2):
        try:
            raw = call_fn(attempt=attempt)
        except Exception as exc:
            errors.append(f"Attempt {attempt}: call_fn raised {type(exc).__name__}: {exc}")
            continue

        guard_result = validate_output(raw, schema_cls, many=many)
        if guard_result.ok:
            return StructuredRetryResult(
                ok=True,
                data=guard_result.validated if many else _first_or_none(guard_result.validated),
                attempts=attempt,
                used_fallback=False,
                errors=errors,
                schema_name=schema_cls.__name__,
            )

        errors.extend(_fmt_schema_errors(guard_result))

    # All attempts exhausted — try fallback
    if fallback_fn is not None:
        try:
            raw = fallback_fn()
        except Exception as exc:
            errors.append(f"Fallback: fallback_fn raised {type(exc).__name__}: {exc}")
            return StructuredRetryResult(
                ok=False, data=None, attempts=max_retries + 1,
                used_fallback=True, errors=errors, schema_name=schema_cls.__name__,
            )

        guard_result = validate_output(raw, schema_cls, many=many)
        if guard_result.ok:
            return StructuredRetryResult(
                ok=True,
                data=guard_result.validated if many else _first_or_none(guard_result.validated),
                attempts=max_retries + 1,
                used_fallback=True,
                errors=errors,
                schema_name=schema_cls.__name__,
            )

        errors.extend(_fmt_schema_errors(guard_result))
        return StructuredRetryResult(
            ok=False, data=None, attempts=max_retries + 1,
            used_fallback=True, errors=errors, schema_name=schema_cls.__name__,
        )

    return StructuredRetryResult(
        ok=False, data=None, attempts=max_retries + 1,
        used_fallback=False, errors=errors, schema_name=schema_cls.__name__,
    )


def _first_or_none(items: list[Any]) -> Any | None:
    return items[0] if items else None
