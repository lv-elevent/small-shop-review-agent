"""Tests for services/workflow_service.py — full pipeline via temp DB."""
from __future__ import annotations

from pathlib import Path

import pytest

from small_shop_agent.services.review_service import ReviewService
from small_shop_agent.services.workflow_service import WorkflowService

_SAMPLE_CSV = (
    Path(__file__).resolve().parents[2]
    / "src" / "small_shop_agent" / "demo" / "sample_reviews.csv"
)


@pytest.fixture
def _batch_id(temp_db):
    """Upload sample CSV into temp DB, return batch_id."""
    result = ReviewService().create_batch(
        str(_SAMPLE_CSV), store_type="coffee_shop", file_name="sample_reviews.csv"
    )
    assert result["success"] is True
    return result["batch_id"]


class TestWorkflowService:
    def test_run_demo_analysis_success(self, temp_db, _batch_id):
        batch_id = _batch_id
        wf = WorkflowService().run_demo_analysis(batch_id)
        assert wf["success"] is True
        s = wf["summary"]
        assert s["review_count"] == 13
        assert s["insight_count"] == 3
        assert s["draft_count"] == 5
        assert s["blocked_count"] == 1
        assert s["evidence_count"] == 5

    def test_get_workflow_status(self, temp_db, _batch_id):
        batch_id = _batch_id
        WorkflowService().run_demo_analysis(batch_id)
        status = WorkflowService().get_workflow_status(batch_id)
        assert status["success"] is True
        assert status["batch_id"] == batch_id
        assert status["batch"] is not None
        assert len(status["traces"]) >= 9
        assert status["counts"]["analysis"] == 13
        assert status["counts"]["insights"] == 3
        assert status["counts"]["drafts"] == 5

    def test_get_workflow_status_nonexistent_batch(self, temp_db):
        status = WorkflowService().get_workflow_status("no-such-batch")
        assert status["success"] is False
        assert "not found" in str(status["error"]).lower()
