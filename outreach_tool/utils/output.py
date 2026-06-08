"""Output persistence and statistics for the outreach tool."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("outreach_tool.output")


@dataclass
class RunStatistics:
    """Aggregated statistics for a single outreach run."""

    run_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None

    companies_found: int = 0
    companies_limited: int = 0
    contacts_found: int = 0
    contacts_enriched: int = 0
    contacts_skipped_dedup: int = 0
    contacts_skipped_safety: int = 0
    emails_sent: int = 0
    emails_failed: int = 0

    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate run duration in seconds."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Serialize statistics to a dictionary."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "companies_found": self.companies_found,
            "companies_limited": self.companies_limited,
            "contacts_found": self.contacts_found,
            "contacts_enriched": self.contacts_enriched,
            "contacts_skipped_dedup": self.contacts_skipped_dedup,
            "contacts_skipped_safety": self.contacts_skipped_safety,
            "emails_sent": self.emails_sent,
            "emails_failed": self.emails_failed,
            "errors": self.errors,
        }


class RunResults:
    """Persist run results to JSON files."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_run_result(
        self,
        run_id: str,
        data: dict[str, Any],
    ) -> Path:
        """Save a run's result to a JSON file.

        Args:
            run_id: Unique identifier for the run.
            data: The data to serialize.

        Returns:
            Path to the saved file.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"run_{run_id}_{timestamp}.json"
        filepath = self.output_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info("Saved run result to %s", filepath)
        except Exception:
            logger.exception("Failed to save run result to %s", filepath)
            raise

        return filepath

    def save_statistics(self, stats: RunStatistics) -> Path:
        """Save run statistics.

        Args:
            stats: The statistics to save.

        Returns:
            Path to the saved file.
        """
        filepath = self.output_dir / f"stats_{stats.run_id}.json"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(stats.to_dict(), f, indent=2, default=str)
            logger.info("Saved run statistics to %s", filepath)
        except Exception:
            logger.exception("Failed to save statistics to %s", filepath)
            raise
        return filepath
