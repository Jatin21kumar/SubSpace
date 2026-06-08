"""Shared HTTP client with retries, rate limiting, and pagination."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, override

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import outreach_tool.core.config as core_config

logger = logging.getLogger("outreach_tool.http_client")


class RateLimiter:
    """Simple async rate limiter using a leaky bucket approach."""

    def __init__(self, requests_per_second: float) -> None:
        self._interval = 1.0 / requests_per_second
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until the next request is allowed."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self._interval:
                wait_time = self._interval - elapsed
                await asyncio.sleep(wait_time)
            self._last_request_time = asyncio.get_event_loop().time()


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: int = 0, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class HTTPClient:
    """Shared async HTTP client with retries and rate limiting."""

    def __init__(
        self,
        *,
        base_url: str,
        headers: dict[str, str] | None = None,
        requests_per_second: float | None = None,
        max_retries: int | None = None,
        retry_backoff_factor: float | None = None,
        retry_statuses: tuple[int, ...] | None = None,
        timeout: float = 30.0,
        name: str = "http_client",
        config: Config | None = None,
    ) -> None:
        self.config = config or core_config.get_config()
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.rps = requests_per_second or self.config.requests_per_second
        self.max_retries = max_retries or self.config.max_retries
        self.backoff_factor = retry_backoff_factor or self.config.retry_backoff_factor
        self.retry_statuses = retry_statuses or self.config.retry_statuses
        self.timeout = timeout
        self.name = name
        self._rate_limiter = RateLimiter(self.rps)
        self._client: httpx.AsyncClient | None = None
        self._logger = logging.getLogger(f"outreach_tool.{name}")

    async def __aenter__(self) -> HTTPClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_retry_predicate(self) -> Any:
        """Build a retry predicate based on configuration."""
        return retry_if_exception_type(
            (APIError, httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute a single HTTP request with rate limiting and retries."""
        assert self._client is not None, "Client must be used as an async context manager"

        await self._rate_limiter.acquire()

        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        url = f"{self.base_url}{path}"
        self._logger.debug(
            "%s %s", method, path, extra={"params": params, "headers": dict(request_headers)}
        )

        try:
            response = await self._client.request(
                method,
                url,
                params=params,
                json=json_data,
                headers=request_headers,
            )
            response.raise_for_status()
            self._logger.debug(
                "%s %s → %d", method, path, response.status_code
            )
            return response
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text
            
            # Extract rate limit headers for better error reporting
            quota_info = []
            for h in exc.response.headers:
                hl = h.lower()
                if any(x in hl for x in ("ratelimit", "request-left", "reset-seconds", "retry-after", "quota")):
                    quota_info.append(f"{h}: {exc.response.headers[h]}")
            
            quota_msg = f" | Quota info: {', '.join(quota_info)}" if quota_info else ""
            
            self._logger.warning(
                "HTTP error: %s %s → %d: %s%s", method, path, status, body, quota_msg
            )
            if status in self.retry_statuses:
                raise APIError(f"HTTP {status}: {body}{quota_msg}", status_code=status, response_body=body)
            raise
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            self._logger.warning("Connection error: %s %s → %s", method, path, exc)
            raise

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with automatic retries."""

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=self.backoff_factor, min=1, max=60),
            retry=self._get_retry_predicate(),
            reraise=True,
        )
        async def _do_request() -> httpx.Response:
            return await self._request(method, path, params=params, json_data=json_data, headers=headers)

        return await _do_request()

    async def paginated_get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        page_key: str = "page",
        limit_key: str = "limit",
        page_size: int | None = None,
        max_pages: int | None = None,
        response_items_key: str | None = None,
        next_page_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute paginated GET requests and collect all results."""
        page = 1
        all_results: list[dict[str, Any]] = []
        effective_page_size = page_size or self.config.page_size
        effective_max_pages = max_pages or self.config.max_pages

        while page <= effective_max_pages:
            request_params = {**(params or {}), page_key: page, limit_key: effective_page_size}
            response = await self.request("GET", path, params=request_params)
            data = response.json()

            if response_items_key:
                items = data.get(response_items_key, [])
            else:
                items = data if isinstance(data, list) else []

            if not items:
                break

            all_results.extend(items)
            self._logger.info(
                "Fetched page %d, %d items (total: %d)",
                page,
                len(items),
                len(all_results),
            )

            # Check for next page indicator
            has_next = False
            if next_page_key and data.get(next_page_key):
                has_next = True
            elif len(items) >= effective_page_size:
                has_next = True

            if not has_next:
                break
            page += 1

        return all_results
