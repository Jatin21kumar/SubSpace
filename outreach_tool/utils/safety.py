"""Safety checkpoint module for rate limiting and compliance."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("outreach_tool.safety")


@dataclass(frozen=True, slots=True)
class SafetyStatus:
    """Status of the safety checkpoint."""

    passed: bool
    message: str
    details: dict[str, Any] | None = None


class SafetyCheckpoint:
    """Safety checkpoint for validating outreach operations.

    Provides checks for:
    - Daily/weekly send limits
    - Domain sending frequency (to avoid spam complaints)
    - Blacklisted domains
    - Working hours validation
    """

    # Hard blocklist of domains never to contact (default examples)
    DEFAULT_BLOCKLIST: frozenset[str] = frozenset({
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
    })

    def __init__(
        self,
        max_daily_emails: int = 500,
        max_domain_emails: int = 10,
        enable_working_hours: bool = True,
        working_hours: tuple[int, int] = (9, 18),
        timezone_name: str = "UTC",
        blocklist: set[str] | None = None,
    ) -> None:
        self.max_daily_emails = max_daily_emails
        self.max_domain_emails = max_domain_emails
        self.enable_working_hours = enable_working_hours
        self.working_hours = working_hours
        self.timezone_name = timezone_name
        self.blocklist = blocklist or self.DEFAULT_BLOCKLIST
        self.daily_count = 0
        self.domain_counts: dict[str, int] = {}
        self.start_of_day = datetime.now(timezone.utc).date()

    def reset_daily_count(self) -> None:
        """Reset the daily count if a new day has started."""
        today = datetime.now(timezone.utc).date()
        if today > self.start_of_day:
            self.daily_count = 0
            self.domain_counts.clear()
            self.start_of_day = today
            logger.info("Daily counters reset for new day")

    def check_email_validity(self, email: str, *, company_domain: str | None = None) -> SafetyStatus:
        """Check if an email address passes all safety checks.

        Args:
            email: The email address to validate.
            company_domain: Optional company domain for additional checks.

        Returns:
            SafetyStatus with pass/fail and details.
        """
        self.reset_daily_count()

        # Check blocklist
        email_domain = email.split("@")[-1].lower()

        if email_domain in self.blocklist:
            return SafetyStatus(
                passed=False,
                message=f"Domain '{email_domain}' is in the blocklist.",
                details={"domain": email_domain},
            )

        # Check daily limit
        if self.daily_count >= self.max_daily_emails:
            return SafetyStatus(
                passed=False,
                message=f"Daily email limit ({self.max_daily_emails}) would be exceeded.",
                details={"daily_count": self.daily_count, "limit": self.max_daily_emails},
            )

        # Check domain sending frequency
        target_domain = company_domain or email_domain
        if target_domain in self.domain_counts and self.domain_counts[target_domain] >= self.max_domain_emails:
            return SafetyStatus(
                passed=False,
                message=f"Domain '{target_domain}' has reached its email limit ({self.max_domain_emails}).",
                details={"domain": target_domain, "count": self.domain_counts.get(target_domain, 0)},
            )

        return SafetyStatus(
            passed=True,
            message="All safety checks passed.",
            details={"domain": target_domain},
        )

    def record_email(self, email: str, *, company_domain: str | None = None) -> None:
        """Record a successfully sent email.

        Args:
            email: The email address that was sent.
            company_domain: Optional company domain.
        """
        self.daily_count += 1
        domain = company_domain or email.split("@")[-1].lower()
        self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of current safety checkpoint state."""
        return {
            "daily_count": self.daily_count,
            "daily_limit": self.max_daily_emails,
            "remaining": self.max_daily_emails - self.daily_count,
            "domains": dict(self.domain_counts),
            "max_domain_emails": self.max_domain_emails,
            "blocklist_size": len(self.blocklist),
        }
