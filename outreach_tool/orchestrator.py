"""Orchestrator that coordinates the outreach workflow.

Workflow:
    Seed Domain
    → Ocean.io similar companies
    → Prospeo search-person
    → Prospeo enrich-person
    → Safety checkpoint
    → Brevo email sending
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from outreach_tool.apis.brevo import BrevoClient, EmailResult
from outreach_tool.apis.oceanio import OceanIOClient
from outreach_tool.apis.prospeo import EnrichedProfile, PersonProfile, ProspeoClient
import outreach_tool.core.config as core_config
from outreach_tool.core.logging_config import setup_logging
from outreach_tool.utils.console import console
from outreach_tool.utils.dedup import DedupStore
from outreach_tool.utils.output import RunResults, RunStatistics
from outreach_tool.utils.safety import SafetyCheckpoint

logger = logging.getLogger("outreach_tool.orchestrator")


@dataclass
class OutreachContact:
    """A contact ready for email outreach."""

    name: str = ""
    email: str = ""
    title: str | None = None
    company_name: str = ""
    company_domain: str = ""
    status: str = "pending"  # pending, enriched, skipped, sent, failed
    error: str | None = None
    enrichment_data: dict[str, Any] = field(default_factory=dict)


class OutreachOrchestrator:
    """Orchestrates the full outreach workflow."""

    def __init__(
        self,
        *,
        run_id: str | None = None,
        max_companies: int | None = None,
        max_contacts_per_company: int | None = None,
        output_dir: str | None = None,
        config: Config | None = None,
    ) -> None:
        self.config = config or core_config.get_config()
        self.run_id = run_id or str(uuid4())[:8]
        self.max_companies = max_companies or self.config.max_companies
        self.max_contacts = max_contacts_per_company or self.config.max_contacts_per_company
        self.output_dir = output_dir or str(self.config.output_dir)

        # Initialize components
        self.stats = RunStatistics(run_id=self.run_id)
        self.results = RunResults(self.config.output_dir)
        self.safety = SafetyCheckpoint()
        self.dedup = DedupStore(
            self.config.output_dir / "sent_emails.json",
            retention_days=self.config.email_deduplication_window_days,
        )
        logger.info(
            "Orchestrator initialized (run_id=%s, max_companies=%d, max_contacts=%d)",
            self.run_id, self.max_companies, self.max_contacts,
        )

    def _should_stop(self) -> bool:
        """Check if the run should stop based on company/contact limits."""
        return self.stats.companies_found >= self.max_companies

    async def run(  # noqa: C901, PLR0913
        self,
        *,
        seed_domain: str,
        email_subject: str,
        email_html: str,
        from_email: str,
        from_name: str | None = None,
        to_name: str | None = None,
        job_title_filter: str | None = None,
        seniority_filter: str | None = None,
        department_filter: str | None = None,
    ) -> dict[str, Any]:
        """Execute the full outreach workflow.

        Args:
            seed_domain: Starting company domain for similar company lookup.
            email_subject: Subject line for the email.
            email_html: HTML content of the email.
            from_email: Sender email address.
            from_name: Sender display name.
            to_name: Overrides the recipient display name.
            job_title_filter: Filter Prospeo results by job title.
            seniority_filter: Filter Prospeo results by seniority.
            department_filter: Filter Prospeo results by department.

        Returns:
            Dict containing run statistics and results summary.
        """
        console.starting_outreach(seed_domain)
        logger.info("🚀 Starting outreach run %s for domain: %s", self.run_id, seed_domain)

        all_contacts: list[OutreachContact] = []

        try:
            async with OceanIOClient(config=self.config) as ocean, \
                       ProspeoClient(config=self.config) as prospeo, \
                       BrevoClient(config=self.config) as brevo:
                # Step 1: Find similar companies via Ocean.io
                console.finding_companies()
                similar_companies = await ocean.find_similar_companies(seed_domain)
                self.stats.companies_found = len(similar_companies)

                if len(similar_companies) > self.max_companies:
                    similar_companies = similar_companies[: self.max_companies]
                    self.stats.companies_limited = self.max_companies
                else:
                    self.stats.companies_limited = len(similar_companies)

                console.found_companies(self.stats.companies_found)
                console.companies_selected(similar_companies)
                console.section()
                logger.info("🏢 Found %d companies to process", self.stats.companies_limited)

                # Step 2 & 3: For each company, find and enrich contacts
                for idx, company in enumerate(similar_companies, 1):
                    if idx > self.max_companies:
                        logger.info("Reached max companies limit (%d)", self.max_companies)
                        break

                    console.processing_company(company.name)
                    logger.info(
                        "Processing company %d/%d: %s (%s)",
                        idx, self.stats.companies_limited, company.name, company.domain,
                    )

                    # Search for persons at the company
                    persons = await prospeo.search_persons(
                        company.domain,
                        job_title=job_title_filter,
                        seniority=seniority_filter,
                        department=department_filter,
                        max_results=self.max_contacts,
                    )

                    for person in persons:
                        contact = OutreachContact(
                            name=f"{person.first_name or ''} {person.last_name or ''}".strip(),
                            email=person.email or "",
                            title=person.title,
                            company_name=company.name,
                            company_domain=company.domain,
                        )

                        if not contact.email:
                            logger.debug("Skipping contact without email: %s", contact.name)
                            continue

                        # Check deduplication
                        if self.dedup.is_duplicate(contact.email):
                            self.stats.contacts_skipped_dedup += 1
                            contact.status = "skipped_dedup"
                            contact.error = "Previously contacted within retention window"
                            logger.debug("Skipping duplicate email: %s", contact.email)
                            continue

                        # Check safety checkpoint
                        safety_status = self.safety.check_email_validity(
                            contact.email, company_domain=company.domain
                        )
                        if not safety_status.passed:
                            self.stats.contacts_skipped_safety += 1
                            contact.status = "skipped_safety"
                            contact.error = safety_status.message
                            logger.debug("Safety check failed for %s: %s", contact.email, safety_status.message)
                            continue

                        console.contact_found(contact.name, contact.title)

                        # Step 4: Enrich person via Prospeo
                        enriched = await prospeo.enrich_person(
                            email=contact.email,
                            first_name=person.first_name,
                            last_name=person.last_name,
                            company_domain=company.domain,
                            person_id=person.person_id,
                        )

                        if enriched:
                            self.stats.contacts_enriched += 1
                            contact.enrichment_data = {
                                "title": enriched.title,
                                "seniority": enriched.seniority,
                                "department": enriched.department,
                                "phone": enriched.phone,
                            }
                            if enriched.email_status:
                                contact.enrichment_data["email_status"] = enriched.email_status
                            console.contact_enriched()

                        all_contacts.append(contact)
                        self.stats.contacts_found += 1

                console.summary_pre_send(self.stats.contacts_found, self.stats.contacts_enriched)
                logger.info("👤 Found %d valid contacts across %d companies", self.stats.contacts_found, self.stats.companies_limited)

                if all_contacts:
                    confirm = console.prompt(f"Found {len(all_contacts)} emails. Send emails? (y/n)").strip().lower()
                    if confirm != "y":
                        logger.info("Aborted by user")
                        return self._build_result_summary(all_contacts)

                # Step 5: Send emails via Brevo
                console.sending_emails()
                for contact in [c for c in all_contacts if c.status == "pending"]:
                    # Render personalized template
                    first_name = contact.name.split()[0] if contact.name else ""
                    personalized_html = email_html.replace("{{first_name}}", first_name)
                    personalized_html = personalized_html.replace("{{full_name}}", contact.name or "")
                    personalized_html = personalized_html.replace("{{job_title}}", contact.title or "")
                    personalized_html = personalized_html.replace("{{company_name}}", contact.company_name or "")

                    result = await brevo.send_email(
                        to_email=contact.email,
                        to_name=contact.name or to_name,
                        from_email=from_email,
                        from_name=from_name,
                        subject=email_subject,
                        html_content=personalized_html,
                    )

                    if result.success:
                        contact.status = "sent"
                        self.stats.emails_sent += 1
                        self.safety.record_email(contact.email, company_domain=contact.company_domain)
                        self.dedup.add(contact.email, company_domain=contact.company_domain, run_id=self.run_id)
                        console.email_sent(contact.name)
                        logger.info("✅ Email sent to %s", contact.email)
                    else:
                        contact.status = "failed"
                        contact.error = result.error_message
                        self.stats.emails_failed += 1
                        console.email_failed(contact.name, result.error_message)
                        logger.error("❌ Failed to send to %s: %s", contact.email, result.error_message)

        except Exception as exc:
            logger.exception("Orchestrator failed during run %s", self.run_id)
            self.stats.errors.append(str(exc))

        finally:
            # Finalize statistics
            self.stats.ended_at = datetime.now(timezone.utc)
            self.dedup.close()

        return self._build_result_summary(all_contacts)

    def _build_result_summary(self, contacts: list[OutreachContact]) -> dict[str, Any]:
        """Build the final result summary with statistics."""
        return {
            "run_id": self.run_id,
            "statistics": self.stats.to_dict(),
            "contacts": [
                {
                    "name": c.name,
                    "email": c.email,
                    "company": c.company_name,
                    "status": c.status,
                    "error": c.error,
                    "enrichment": c.enrichment_data,
                }
                for c in contacts
            ],
        }
