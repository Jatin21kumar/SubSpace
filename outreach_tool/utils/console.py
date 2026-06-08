"""Clean console output for the outreach tool."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from outreach_tool.orchestrator import OutreachContact


class Console:
    """Helper for clean, user-facing console output."""

    @staticmethod
    def info(message: str) -> None:
        """Print a clean info message to stdout."""
        print(message)

    @staticmethod
    def success(message: str) -> None:
        """Print a success message, often with an emoji."""
        print(f"✓ {message}")

    @staticmethod
    def error(message: str) -> None:
        """Print an error message."""
        print(f"❌ {message}", file=sys.stderr)

    @staticmethod
    def section(title: str | None = None) -> None:
        """Print a section header or separator."""
        if title:
            print(f"\n--- {title} ---")
        else:
            print("\n" + "─" * 30)

    @staticmethod
    def prompt(message: str) -> str:
        """Prompt the user for input."""
        return input(f"\n{message} ")

    @staticmethod
    def starting_outreach(seed_domain: str) -> None:
        """Print the starting message."""
        print(f"🚀 Starting outreach for: {seed_domain}\n")

    @staticmethod
    def finding_companies() -> None:
        """Print the finding companies message."""
        print("🔍 Finding similar companies...")

    @staticmethod
    def found_companies(count: int) -> None:
        """Print the number of companies found."""
        print(f"✓ Found {count} similar companies\n")

    @staticmethod
    def companies_selected(companies: list[Any]) -> None:
        """Print the list of selected companies."""
        print("🏢 Companies selected:")
        for company in companies:
            print(f"  • {company.name} ({company.domain})")

    @staticmethod
    def processing_company(name: str) -> None:
        """Print the current company being processed."""
        print(f"\n🏢 Processing {name}")

    @staticmethod
    def contact_found(name: str, title: str | None) -> None:
        """Print a contact found at a company."""
        title_str = f" — {title}" if title else ""
        print(f"   👤 {name}{title_str}")

    @staticmethod
    def contact_enriched() -> None:
        """Print a contact enrichment success message."""
        print("   ✓ Contact enriched")

    @staticmethod
    def summary_pre_send(contacts_found: int, contacts_enriched: int) -> None:
        """Print a summary before sending emails."""
        print("\n" + "─" * 30)
        print(f"\n👥 Contacts discovered: {contacts_found}")
        print(f"✅ Contacts enriched: {contacts_enriched}")

    @staticmethod
    def sending_emails() -> None:
        """Print the sending emails message."""
        print("\n📧 Sending emails...\n")

    @staticmethod
    def email_sent(name: str) -> None:
        """Print an email sent message."""
        print(f"✓ Sent to {name}")

    @staticmethod
    def email_failed(name: str, error: str) -> None:
        """Print an email failed message."""
        print(f"❌ Failed to send to {name}: {error}")

    @staticmethod
    def final_summary(
        seed_domain: str,
        stats: dict[str, Any],
        output_file: str | None = None,
    ) -> None:
        """Print the final outreach summary."""
        print("\n" + "=" * 50)
        print("📊 Outreach Summary")
        print("=" * 50 + "\n")

        print(f"Seed Domain:        {seed_domain}")
        print(f"Companies Found:    {stats.get('companies_found', 0)}")
        print(f"Companies Used:     {stats.get('companies_limited', 0)}")
        print()
        print(f"Contacts Found:     {stats.get('contacts_found', 0)}")
        print(f"Contacts Enriched:  {stats.get('contacts_enriched', 0)}")
        print()
        print(f"Emails Sent:        {stats.get('emails_sent', 0)}")
        print(f"Emails Failed:      {stats.get('emails_failed', 0)}")
        print()
        if output_file:
            print(f"Output:\n{output_file}")

        print("\n" + "=" * 50)


console = Console()
