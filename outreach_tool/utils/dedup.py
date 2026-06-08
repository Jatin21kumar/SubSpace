"""Email deduplication using a persistent store."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("outreach_tool.dedup")


@dataclass(frozen=True, slots=True)
class SentRecord:
    """Record of a previously sent email."""

    email: str
    sent_at: datetime
    company_domain: str | None = None
    run_id: str | None = None


class DedupStore:
    """Persistent store for tracking sent emails.

    Uses a JSON file to persist deduplication data across runs.
    Maintains an in-memory cache for fast lookups.
    """

    def __init__(self, store_path: Path, retention_days: int = 30) -> None:
        self.store_path = Path(store_path)
        self.retention_delta = timedelta(days=retention_days)
        self._records: dict[str, SentRecord] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        """Load existing records from disk."""
        if not self.store_path.exists():
            return
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
            cutoff = datetime.now(timezone.utc) - self.retention_delta
            for email, data in raw.items():
                sent_at = datetime.fromisoformat(data["sent_at"])
                if sent_at >= cutoff:
                    self._records[email.lower()] = SentRecord(
                        email=email,
                        sent_at=sent_at,
                        company_domain=data.get("company_domain"),
                        run_id=data.get("run_id"),
                    )
            logger.info("Loaded %d dedup records from %s", len(self._records), self.store_path)
        except Exception:
            logger.exception("Failed to load dedup store from %s", self.store_path)

    def _save(self) -> None:
        """Persist records to disk."""
        if not self._dirty:
            return
        raw: dict[str, dict[str, Any]] = {}
        for email, record in self._records.items():
            data: dict[str, Any] = {"sent_at": record.sent_at.isoformat()}
            if record.company_domain:
                data["company_domain"] = record.company_domain
            if record.run_id:
                data["run_id"] = record.run_id
            raw[email] = data
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self.store_path.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")
            self._dirty = False
            logger.debug("Saved %d dedup records", len(self._records))
        except Exception:
            logger.exception("Failed to save dedup store to %s", self.store_path)

    def is_duplicate(self, email: str) -> bool:
        """Check if an email address has already been contacted recently.

        Args:
            email: The email address to check.

        Returns:
            True if the email was already sent within the retention window.
        """
        normalized = email.lower().strip()
        if normalized in self._records:
            record = self._records[normalized]
            if datetime.now(timezone.utc) - record.sent_at <= self.retention_delta:
                return True
            else:
                # Expired record, remove it
                del self._records[normalized]
                self._dirty = True
        return False

    def add(self, email: str, *, company_domain: str | None = None, run_id: str | None = None) -> None:
        """Record a newly sent email.

        Args:
            email: The email address that was sent.
            company_domain: Optional associated company domain.
            run_id: Optional run identifier for tracking.
        """
        normalized = email.lower().strip()
        self._records[normalized] = SentRecord(
            email=email,
            sent_at=datetime.now(timezone.utc),
            company_domain=company_domain,
            run_id=run_id,
        )
        self._dirty = True
        logger.debug("Added dedup record for %s", email)

    def get_stats(self) -> dict[str, Any]:
        """Return deduplication statistics."""
        return {
            "total_tracked": len(self._records),
            "store_path": str(self.store_path),
            "retention_days": self.retention_delta.days,
        }

    def close(self) -> None:
        """Persist any pending changes and close the store."""
        self._save()

    def __enter__(self) -> DedupStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
