"""Ocean.io API client for finding similar companies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import outreach_tool.core.config as core_config
from outreach_tool.core.http_client import HTTPClient

logger = logging.getLogger("outreach_tool.oceanio")


@dataclass(frozen=True, slots=True)
class Company:
    """Represents a company from Ocean.io."""

    name: str
    domain: str
    industry: str | None = None
    employee_count: int | None = None
    company_size: str | None = None
    location: str | None = None
    ocean_id: str | None = None
    raw_data: dict[str, Any] | None = None


class OceanIOClient:
    """Client for the Ocean.io API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        config: Config | None = None,
    ) -> None:
        self.config = config or core_config.get_config()
        self.api_key = api_key or self.config.ocean_api_key
        self.base_url = base_url or self.config.ocean_base_url
        self._client: HTTPClient | None = None

    async def __aenter__(self) -> OceanIOClient:
        self._client = HTTPClient(
            base_url=self.base_url,
            headers={
                "X-Api-Token": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            name="oceanio",
            config=self.config,
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.__aexit__(*args)
            self._client = None

    async def find_similar_companies(
        self,
        domain: str,
        *,
        limit: int | None = None,
        page_size: int | None = None,
        max_pages: int | None = None,
    ) -> list[Company]:
        """Find companies similar to the given domain using Lookalike Search.

        Args:
            domain: The seed company domain (e.g., "example.com").
            limit: Maximum number of companies to return.
            page_size: Number of results per page.
            max_pages: Maximum pages to fetch.

        Returns:
            List of similar companies.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        logger.info("Finding similar companies to domain: %s", domain)

        effective_page_size = page_size or self.config.page_size
        effective_max_pages = max_pages or self.config.max_pages
        effective_limit = limit or self.config.max_companies

        companies: list[Company] = []
        search_after: str | None = None
        pages_fetched = 0

        while pages_fetched < effective_max_pages:
            payload: dict[str, Any] = {
                "companiesFilters": {
                    "lookalikeDomains": [domain]
                },
                "size": min(effective_page_size, 100),
                "fields": ["name", "domain", "industries", "companySize", "primaryCountry"],
            }
            if search_after:
                payload["searchAfter"] = search_after

            # V3 Lookalike search uses POST /search/companies
            response = await self._client.request("POST", "/search/companies", json_data=payload)
            data = response.json()
            
            raw_items = data.get("companies", [])
            if not raw_items:
                break

            for raw in raw_items:
                # v3 returns company data nested under 'company' key
                company_data = raw.get("company", {})
                
                # Map industries list to single industry string
                industries = company_data.get("industries", [])
                industry = industries[0] if industries and isinstance(industries, list) else None
                
                company = Company(
                    name=company_data.get("name", "") or company_data.get("domain", ""),
                    domain=company_data.get("domain", ""),
                    industry=industry,
                    employee_count=None,  # Deprecated in favor of company_size in V3
                    company_size=company_data.get("companySize"),
                    location=company_data.get("primaryCountry"),
                    ocean_id=company_data.get("domain"), # Use domain as ID if no explicit ID
                    raw_data=raw,
                )
                companies.append(company)
                
                if effective_limit and len(companies) >= effective_limit:
                    break
            
            if effective_limit and len(companies) >= effective_limit:
                break
                
            search_after = data.get("searchAfter")
            if not search_after:
                break
            
            pages_fetched += 1

        logger.info("Found %d similar companies for %s", len(companies), domain)
        return companies
