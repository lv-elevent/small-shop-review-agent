"""ReviewService — CSV upload, validation, cleaning, and persistence pipeline."""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import IO

import pandas as pd
from loguru import logger

from small_shop_agent.storage.repositories.batch_repository import BatchRepository
from small_shop_agent.storage.repositories.review_repository import ReviewRepository
from small_shop_agent.storage.repositories.trace_repository import TraceRepository
from small_shop_agent.harness.input.input_contracts import REQUIRED_COLUMNS
from small_shop_agent.harness.input.csv_validator import validate_csv_schema, validate_and_clean
from small_shop_agent.core.time_utils import now_iso

_ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]


def _read_csv(file_source: str | Path | IO[bytes] | bytes, file_name: str = "") -> tuple[pd.DataFrame | None, str | None]:
    """
    Read a CSV from a file path, file-like object, or bytes.
    Returns (DataFrame, None) on success or (None, error_message) on failure.
    """
    if isinstance(file_source, bytes):
        content = file_source
    elif isinstance(file_source, (str, Path)):
        content = Path(file_source).read_bytes()
    else:
        content = file_source.read()

    for enc in _ENCODINGS:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=enc)
            if df.empty:
                return None, "CSV file is empty (no rows)."
            return df, None
        except Exception:
            continue

    return None, "Unable to parse CSV file. Tried encodings: " + ", ".join(_ENCODINGS)


class ReviewService:
    """Handles CSV ingestion, validation, cleaning, and review persistence."""

    def __init__(self) -> None:
        self._batch_repo = BatchRepository()
        self._review_repo = ReviewRepository()
        self._trace_repo = TraceRepository()

    # ── Public API ──────────────────────────────────────────────────────────

    def validate_csv(self, file_source: str | Path | IO[bytes] | bytes,
                     file_name: str = "") -> dict:
        """Validate a CSV file without persisting. Returns structured result."""
        df, err = _read_csv(file_source, file_name)
        if err is not None:
            return {"success": False, "batch_id": None, "validation": {}, "message": err}

        schema_err = validate_csv_schema(df)
        if schema_err:
            return schema_err

        _, stats = validate_and_clean(df)
        return {
            "success": True,
            "batch_id": None,
            "validation": stats,
            "message": "CSV validated successfully.",
        }

    def create_batch(
        self,
        file_source: str | Path | IO[bytes] | bytes,
        store_type: str = "coffee_shop",
        file_name: str = "",
    ) -> dict:
        """
        Full CSV ingestion pipeline:
        1. Read CSV
        2. Validate schema
        3. Clean and validate rows
        4. Write batch, reviews, and traces to DB
        """
        df, err = _read_csv(file_source, file_name)
        if err is not None:
            return {"success": False, "batch_id": None, "validation": {}, "message": err}

        # Schema validation — block early if required columns missing
        schema_err = validate_csv_schema(df)
        if schema_err:
            return schema_err

        # Row-level validation and cleaning
        cleaned_df, stats = validate_and_clean(df)

        # Generate batch_id
        batch_id = f"batch-{uuid.uuid4().hex[:8]}"
        trace_id = f"trace-{batch_id}"

        try:
            # 1. Create batch record
            batch_status = "analyzed" if stats["valid_review_count"] > 0 else "uploaded"
            self._batch_repo.create_batch(
                batch_id=batch_id,
                store_type=store_type,
                source_type="csv_upload",
                file_name=file_name,
                total_rows=stats["total_rows"],
                valid_review_count=stats["valid_review_count"],
                duplicate_count=stats["duplicate_count"],
                empty_review_count=stats["empty_review_count"],
                schema_error_count=stats["schema_error_count"],
                status=batch_status,
            )

            # 2. Bulk insert reviews — deduplicate review_id to satisfy UNIQUE constraint
            review_rows = []
            seen_ids: dict[str, int] = {}
            for _, row in cleaned_df.iterrows():
                rid = str(row.get("review_id", ""))
                if rid in seen_ids:
                    seen_ids[rid] += 1
                    rid = f"{rid}_dup{seen_ids[rid]}"
                else:
                    seen_ids[rid] = 0
                review_rows.append({
                    "review_id": rid,
                    "date": str(row.get("date", "")) if pd.notna(row.get("date")) else "",
                    "platform": str(row.get("platform", "")) if pd.notna(row.get("platform")) else "",
                    "rating": int(row["rating"]),  # safe: already cleaned to int 1-5
                    "review_text": str(row.get("review_text", "")) if pd.notna(row.get("review_text")) else "",
                    "cleaned_text": str(row.get("cleaned_text", "")),
                    "is_empty": int(row.get("is_empty", 0)),
                    "is_duplicate": int(row.get("is_duplicate", 0)),
                    "is_valid": int(row.get("is_valid", 0)),
                })
            self._review_repo.bulk_insert_reviews(batch_id, review_rows)

            # 3. Write traces
            self._trace_repo.log_step(
                trace_id=trace_id,
                batch_id=batch_id,
                step_name="input_validation",
                status="passed" if stats["schema_error_count"] == 0 else "warning",
                input_summary=f"{file_name} / {stats['total_rows']} rows",
                output_summary=(
                    f"valid={stats['valid_review_count']}, "
                    f"invalid_rating={stats['invalid_rating_count']}, "
                    f"schema_errors={stats['schema_error_count']}"
                ),
                latency_ms=0,
                model_name="rule_based",
            )

            cleaning_status = "warning" if (
                stats["empty_review_count"] > 0 or stats["duplicate_count"] > 0
            ) else "passed"
            self._trace_repo.log_step(
                trace_id=trace_id,
                batch_id=batch_id,
                step_name="data_cleaning",
                status=cleaning_status,
                input_summary=f"{stats['total_rows']} rows",
                output_summary=(
                    f"valid={stats['valid_review_count']}, "
                    f"empty={stats['empty_review_count']}, "
                    f"duplicate={stats['duplicate_count']}"
                ),
                latency_ms=0,
                model_name="rule_based",
            )

            # 4. Build result message
            msg_parts = [f"CSV uploaded: {stats['total_rows']} rows, {stats['valid_review_count']} valid."]
            if stats["duplicate_count"] > 0:
                msg_parts.append(f"{stats['duplicate_count']} duplicates skipped.")
            if stats["empty_review_count"] > 0:
                msg_parts.append(f"{stats['empty_review_count']} empty reviews skipped.")
            if stats["invalid_rating_count"] > 0:
                msg_parts.append(f"{stats['invalid_rating_count']} invalid ratings skipped.")

            return {
                "success": True,
                "batch_id": batch_id,
                "validation": stats,
                "message": " ".join(msg_parts),
            }

        except Exception as exc:
            logger.error(f"create_batch failed: {exc}")
            return {
                "success": False,
                "batch_id": None,
                "validation": stats,
                "message": f"Database error during batch creation: {exc}",
            }

    def list_reviews(self, batch_id: str, valid_only: bool = False) -> list[dict]:
        """List reviews for a batch."""
        return self._review_repo.list_reviews(
            batch_id, is_valid=True if valid_only else None
        )

    def get_review(self, batch_id: str, review_id: str) -> dict | None:
        """Get a single review by batch_id and review_id."""
        return self._review_repo.get_review(batch_id, review_id)

    def get_batch_summary(self, batch_id: str) -> dict | None:
        """Get batch metadata."""
        return self._batch_repo.get_batch(batch_id)
