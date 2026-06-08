"""Prospeo API client for person search and enrichment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import outreach_tool.core.config as core_config
from outreach_tool.core.http_client import HTTPClient

logger = logging.getLogger("outreach_tool.prospeo")


@dataclass(frozen=True, slots=True)
class PersonProfile:
    """Represents a person profile from Prospeo."""

    person_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    phone: str | None = None
    company_domain: str | None = None
    company_name: str | None = None
    raw_data: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EnrichedProfile:
    """Enriched person profile."""

    person_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    email_status: str | None = None
    title: str | None = None
    department: str | None = None
    seniority: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    company_industry: str | None = None
    raw_data: dict[str, Any] | None = None


class ProspeoClient:
    """Client for the Prospeo API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        config: Config | None = None,
    ) -> None:
        self.config = config or core_config.get_config()
        self.api_key = api_key or self.config.prospeo_api_key
        self.base_url = base_url or self.config.prospeo_base_url
        self._client: HTTPClient | None = None

    async def __aenter__(self) -> ProspeoClient:
        self._client = HTTPClient(
            base_url=self.base_url,
            headers={
                "X-KEY": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            name="prospeo",
            config=self.config,
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.__aexit__(*args)
            self._client = None

    async def search_persons(
        self,
        company_domain: str,
        *,
        job_title: str | None = None,
        seniority: str | None = None,
        department: str | None = None,
        max_results: int | None = None,
    ) -> list[PersonProfile]:
        """Search for persons at a company.

        Args:
            company_domain: The target company domain.
            job_title: Optional job title filter.
            seniority: Optional seniority filter (e.g., "director", "vp", "c-level").
            department: Optional department filter (e.g., "sales", "marketing").
            max_results: Maximum number of results to return.

        Returns:
            List of person profiles.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        logger.info("Searching persons at domain: %s", company_domain)

        body: dict[str, Any] = {"filters": {}}
        filters: dict[str, Any] = body["filters"]
        
        # Corrected structure: company.websites.include
        filters["company"] = {"websites": {"include": [company_domain]}}

        if job_title:
            filters["person_job_title"] = {"include": [job_title]}
        if seniority:
            filters["person_seniority"] = {"include": [seniority]}
        if department:
            filters["person_departments"] = {"include": [department]}

        all_results: list[PersonProfile] = []
        page = 1

        while True:
            body["page"] = page
            per_page = min(max_results or self.config.page_size, 100)

            try:
                response = await self._client.request(
                    "POST",
                    "/search-person",
                    json_data=body,
                )
                result = response.json()
            except Exception:
                logger.exception("Failed to search persons for %s", company_domain)
                break

            page_data = result.get("results", [])
            for raw in page_data:
                person_raw = raw.get("person", {}) if isinstance(raw, dict) else {}
                
                # Extract email if it's an object
                email_data = person_raw.get("email")
                email = email_data.get("email") if isinstance(email_data, dict) else email_data
                
                # Extract phone/mobile
                mobile_data = person_raw.get("mobile")
                phone = mobile_data.get("mobile") if isinstance(mobile_data, dict) else person_raw.get("phone")

                profile = PersonProfile(
                    person_id=person_raw.get("id"),
                    first_name=person_raw.get("first_name"),
                    last_name=person_raw.get("last_name"),
                    email=email,
                    title=person_raw.get("current_job_title") or person_raw.get("job_title"),
                    linkedin_url=person_raw.get("linkedin_url"),
                    phone=phone,
                    company_domain=company_domain,
                    raw_data=person_raw,
                )
                all_results.append(profile)

            # Pagination handling
            pagination = result.get("pagination", {})
            total_pages = pagination.get("total_page", page)
            current_page = pagination.get("current_page", page)

            logger.debug(
                "Page %d/%d fetched for %s", current_page, total_pages, company_domain
            )

            if current_page >= total_pages or not page_data:
                break
            page += 1

            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break

        logger.info("Found %d persons at %s", len(all_results), company_domain)
        return all_results

    async def enrich_person(
        self,
        *,
        email: str | None = None,
        linkedin_url: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company_domain: str | None = None,
        person_id: str | None = None,
    ) -> EnrichedProfile | None:
        """Enrich a person's profile using available identifiers.

        Args:
            email: Person's email address.
            linkedin_url: LinkedIn profile URL.
            first_name: First name (requires last_name and company_domain).
            last_name: Last name.
            company_domain: Company domain.
            person_id: Prospeo person ID from Search API.

        Returns:
            Enriched profile or None if enrichment failed.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        body: dict[str, Any] = {"data": {}}
        data = body["data"]
        if person_id:
            data["person_id"] = person_id
        if email:
            data["email"] = email
        if linkedin_url:
            data["linkedin_url"] = linkedin_url
        if first_name and last_name:
            data["first_name"] = first_name
            data["last_name"] = last_name
            if company_domain:
                data["company_domain"] = company_domain
                data["company_website"] = company_domain

        if not data:
            logger.warning("No valid identifiers provided for enrichment")
            return None

        logger.debug("Enriching person: %s", person_id or email or linkedin_url or f"{first_name} {last_name}")

        try:
            response = await self._client.request(
                "POST",
                "/enrich-person",
                json_data=body,
            )
            result = response.json()
        except Exception:
            logger.exception("Failed to enrich person")
            return None

        contact = result.get("contact", result)  # Handle different response structures

        return EnrichedProfile(
            person_id=contact.get("id") or person_id,
            first_name=contact.get("first_name"),
            last_name=contact.get("last_name"),
            email=contact.get("email"),
            email_status=contact.get("email_status"),
            title=contact.get("job_title"),
            department=contact.get("department"),
            seniority=contact.get("seniority"),
            phone=contact.get("phone"),
            linkedin_url=contact.get("linkedin_url"),
            twitter_handle=contact.get("twitter_handle"),
            company_name=contact.get("company_name"),
            company_domain=contact.get("company_domain"),
            company_industry=contact.get("company_industry"),
            raw_data=contact,
        )
