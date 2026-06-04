"""Multi-agent base class -- each Agent is an independent mini-DAG.

Agents receive state from the Orchestrator, run their internal nodes,
and return the mutated state.  Each agent handles its own retry/fallback.
"""
from __future__ import annotations

import inspect
from typing import Any

from small_shop_agent.agent_runtime.state import AgentState


class MultiAgent:
    """Base class for a single-domain agent within the multi-agent workflow.

    Subclasses implement ``run()`` and optionally ``retry_all()``.
    """

    name: str = "base"

    def _dispatch(self, node_fn, state: AgentState, **deps: Any) -> None:
        """Call *node_fn* with only the keyword arguments it accepts."""
        sig = inspect.signature(node_fn)
        accepted = {p for p in sig.parameters if p not in ("self", "state")}
        filtered = {k: v for k, v in deps.items() if k in accepted}
        node_fn(state, **filtered)

    def run(self, state: AgentState, **deps: Any) -> AgentState:
        raise NotImplementedError

    def retry_all(self, state: AgentState, **deps: Any) -> AgentState:
        """Optional: retry the entire agent from scratch."""
        return self.run(state, **deps)
