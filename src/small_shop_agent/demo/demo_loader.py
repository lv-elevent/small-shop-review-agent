"""DemoLoader — loads sample CSV and deterministic mock JSON data for Demo Mode."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any


class DemoLoader:
    """Loads all demo assets from the demo/ package directory."""

    def __init__(self) -> None:
        self._demo_dir = Path(__file__).resolve().parent

    # ── CSV Loading ────────────────────────────────────────────────────

    def load_sample_reviews(self) -> list[dict[str, Any]]:
        """Read sample_reviews.csv and return list of row dicts."""
        path = self._demo_dir / "sample_reviews.csv"
        if not path.exists():
            raise FileNotFoundError(f"Sample CSV not found: {path}")
        text = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    # ── JSON Loading ───────────────────────────────────────────────────

    def load_mock_classification(self) -> list[dict[str, Any]]:
        return self._read_json("mock_classification.json")

    def load_mock_sentiment(self) -> list[dict[str, Any]]:
        return self._read_json("mock_sentiment.json")

    def load_mock_insights(self) -> list[dict[str, Any]]:
        return self._read_json("mock_insights.json")

    def load_mock_replies(self) -> list[dict[str, Any]]:
        return self._read_json("mock_replies.json")

    def load_mock_trace(self) -> list[dict[str, Any]]:
        return self._read_json("mock_trace.json")

    def load_mock_batch(self) -> dict[str, Any]:
        return self._read_json("demo_batch.json")

    # ── Bundled Payload ────────────────────────────────────────────────

    def get_demo_payload(self) -> dict[str, Any]:
        """Return a single dict containing all demo data."""
        return {
            "batch": self.load_mock_batch(),
            "reviews": self.load_sample_reviews(),
            "classification": self.load_mock_classification(),
            "sentiment": self.load_mock_sentiment(),
            "insights": self.load_mock_insights(),
            "replies": self.load_mock_replies(),
            "traces": self.load_mock_trace(),
        }

    # ── Internal Helpers ───────────────────────────────────────────────

    def _read_json(self, filename: str) -> Any:
        path = self._demo_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Mock data file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
