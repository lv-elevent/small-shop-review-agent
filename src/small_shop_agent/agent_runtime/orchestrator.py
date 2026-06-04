"""AgentOrchestrator -- rule-based coordinator for the multi-agent workflow.

Sequences ReviewAgent -> ReplyAgent -> SafetyAgent using shared AgentState.
No LLM needed for orchestration -- the ordering is deterministic.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from small_shop_agent.agent_runtime.state import AgentState
from small_shop_agent.agent_runtime.multi_agent import MultiAgent
from small_shop_agent.agent_runtime.agents.review_agent import ReviewAgent
from small_shop_agent.agent_runtime.agents.reply_agent import ReplyAgent
from small_shop_agent.agent_runtime.agents.safety_agent import SafetyAgent
from small_shop_agent.agent_runtime.graph.nodes import approval_node


class AgentOrchestrator:
    """Orchestrate the multi-agent review workflow."""

    def __init__(self) -> None:
        self._review = ReviewAgent()
        self._reply = ReplyAgent()
        self._safety = SafetyAgent()

    def run(self, state: AgentState, **deps: Any) -> AgentState:
        """Execute ReviewAgent -> ReplyAgent -> SafetyAgent -> approval."""
        logger.info(f"Orchestrator 启动 multi-agent 工作流 batch={state['batch_id']}")

        # Phase 1: Review (analysis + insights + evidence)
        state["current_step"] = "review_agent"
        state = self._review.run(state, provider=deps.pop('review_provider', deps.get('provider')), **deps)

        # Phase 2: Reply (draft generation)
        state["current_step"] = "reply_agent"
        state = self._reply.run(state, provider=deps.pop('reply_provider', deps.get('provider')), **deps)

        # Phase 3: Safety (dual-engine guard)
        state["current_step"] = "safety_agent"
        state = self._safety.run(state, provider=deps.pop('safety_provider', deps.get('provider')), **deps)

        # Terminal: approval
        state["current_step"] = "human_approval"
        approval_node(state)

        error_count = len(state.get("errors", []))
        logger.success(
            f"Orchestrator 完成 batch={state['batch_id']} "
            f"errors={error_count} warnings={len(state.get('warnings', []))}"
        )
        return state
