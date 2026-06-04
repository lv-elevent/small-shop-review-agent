"""Small Shop Review Agent -- FastAPI REST layer.

Serves /api/v1/* endpoints.  The Streamlit UI is the frontend; this
module provides a programmable HTTP API for integration.
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path as FsPath
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

_PROJECT_ROOT = FsPath(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.services.workflow_service import WorkflowService
from small_shop_agent.services.eval_service import EvalService
from small_shop_agent.harness.input.csv_validator import validate_and_clean
from small_shop_agent.agent_runtime.runner import run_with_agent_runtime
from small_shop_agent.core.config import WORKFLOW_RUNTIME

app = FastAPI(title="Small Shop Review Agent API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# POST /api/v1/upload
# ------------------------------------------------------------------

@app.post("/api/v1/upload")
async def upload_reviews(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a CSV of customer reviews. Returns batch_id."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are accepted.")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(422, f"Failed to parse CSV: {exc}")

    df, stats = validate_and_clean(df)
    if stats["valid_review_count"] == 0:
        raise HTTPException(422, "No valid reviews found in CSV.")

    batch_repo = BatchRepository()
    review_repo = ReviewRepository()
    batch_id = f"api-{uuid.uuid4().hex[:8]}"

    batch_repo.create_batch(
        batch_id=batch_id,
        total_rows=stats["total_rows"],
        valid_review_count=stats["valid_review_count"],
        file_name=file.filename,
    )
    review_repo.bulk_insert_reviews(batch_id, df.to_dict("records"))

    return {
        "batch_id": batch_id,
        "total_rows": stats["total_rows"],
        "valid_review_count": stats["valid_review_count"],
        "duplicate_count": stats["duplicate_count"],
        "empty_review_count": stats["empty_review_count"],
    }


# ------------------------------------------------------------------
# POST /api/v1/analyze/{batch_id}
# ------------------------------------------------------------------

@app.post("/api/v1/analyze/{batch_id}")
def analyze_batch(batch_id: str) -> dict[str, Any]:
    """Run the full Agent workflow against batch_id, then auto-eval."""
    mode = "live"

    if WORKFLOW_RUNTIME == "agent_graph":
        state = run_with_agent_runtime(batch_id, mode=mode)
    else:
        wf = WorkflowService()
        state = wf.run_analysis(batch_id, mode=mode)

    if state.get("errors"):
        return {
            "batch_id": batch_id,
            "status": "failed",
            "errors": state["errors"],
        }

    # Auto-trigger eval after workflow completes
    eval_svc = EvalService()
    eval_result = eval_svc.run_eval({"batch_id": batch_id})

    return {
        "batch_id": batch_id,
        "status": "analyzed",
        "warnings": len(state.get("warnings", [])),
        "eval": {
            "eval_run_id": eval_result.get("eval_run_id"),
            "topic_accuracy": eval_result.get("report", {}).get("topic_accuracy"),
            "sentiment_accuracy": eval_result.get("report", {}).get("sentiment_accuracy"),
            "red_team_recall": eval_result.get("report", {}).get("red_team_recall"),
            "unsafe_reply_count": eval_result.get("report", {}).get("unsafe_reply_count"),
        } if eval_result.get("success") else None,
    }


# ------------------------------------------------------------------
# GET /api/v1/batches/{batch_id}/status
# ------------------------------------------------------------------

@app.get("/api/v1/batches/{batch_id}/status")
def batch_status(batch_id: str) -> dict[str, Any]:
    """Return batch status and data counts."""
    wf = WorkflowService()
    return wf.get_workflow_status(batch_id)


# ------------------------------------------------------------------
# GET /api/v1/eval/trend
# ------------------------------------------------------------------

@app.get("/api/v1/eval/trend")
def eval_trend(limit: int = 10) -> list[dict[str, Any]]:
    """Return the last N eval runs as chart-ready trend data."""
    return EvalService().get_eval_trend_data(limit=limit)


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.3.0"}
