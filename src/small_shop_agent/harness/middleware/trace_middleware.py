"""Trace middleware — decorator for automatic step-level trace logging."""
from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable

from small_shop_agent.utils.logger import log_step


def trace_step(step_name: str, batch_id: str = ""):
    """Decorator that logs start/done + latency for a workflow step.

    Usage:
        @trace_step("classification", batch_id="batch-abc")
        def classify(reviews):
            return [...]
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bid = batch_id or kwargs.get("batch_id", "unknown")
            log_step(f"{step_name}_start", bid, step=step_name)
            t0 = time.time()
            try:
                result = func(*args, **kwargs)
                latency_ms = int((time.time() - t0) * 1000)
                log_step(f"{step_name}_done", bid, step=step_name, latency_ms=latency_ms, ok=True)
                return result
            except Exception as exc:
                latency_ms = int((time.time() - t0) * 1000)
                log_step(f"{step_name}_error", bid, step=step_name, latency_ms=latency_ms, error=str(exc))
                raise

        return wrapper

    return decorator
