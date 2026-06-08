"""Brevo (Sendinblue) API client for email sending."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import outreach_tool.core.config as core_config
from outreach_tool.core.http_client import HTTPClient

logger = logging.getLogger("outreach_tool.brevo")


@dataclass(frozen=True, slots=True)
class EmailResult:
    """Result of an email send operation."""

    success: bool
    message_id: str | None = None
    status: str | None = None
    error_message: str | None = None
    recipient: str | None = None


class BrevoClient:
    """Client for the Brevo / Sendinblue API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        config: Config | None = None,
    ) -> None:
        self.config = config or core_config.get_config()
        self.api_key = api_key or self.config.brevo_api_key
        self.base_url = base_url or self.config.brevo_base_url
        self._client: HTTPClient | None = None

    async def __aenter__(self) -> BrevoClient:
        self._client = HTTPClient(
            base_url=self.base_url,
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            name="brevo",
            config=self.config,
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.__aexit__(*args)
            self._client = None

    async def send_email(
        self,
        *,
        to_email: str,
        to_name: str | None = None,
        from_email: str,
        from_name: str | None = None,
        subject: str,
        html_content: str | None = None,
        text_content: str | None = None,
        template_id: int | None = None,
        params: dict[str, Any] | None = None,
        reply_to: str | None = None,
    ) -> EmailResult:
        """Send an email via Brevo.

        Args:
            to_email: Recipient email address.
            to_name: Recipient name.
            from_email: Sender email address.
            from_name: Sender name.
            subject: Email subject.
            html_content: HTML content of the email.
            text_content: Plain text content of the email.
            template_id: Optional Brevo template ID.
            params: Template parameters.
            reply_to: Reply-to email address.

        Returns:
            EmailResult with send status.
        """
        if not self._client:
            raise RuntimeError("Client not initialized.当时是点Use 'async with' context manager.")

        payload: dict[str, Any] = {
            "sender": {"email": from_email, "name": from_name} if from_name else {"email": from_email},
            "to": [{"email": to_email, "name": to_name}] if to_name else [{"email": to_email}],
            "subject": subject,
        }

        if html_content:
            payload["htmlContent"] = html_content
        if text_content:
            payload["textContent"] = text_content
        if template_id:
            payload["templateId"] = template_id
        if params:
            payload["params"] = params
        if reply_to:
            payload["replyTo"] = {"email": reply_to}

        try:
            response = await self._client.request(
                "POST",
                "/smtp/email",
                json_data=payload,
            )
            result = response.json()
            message_id = result.get("messageId")
            return EmailResult(
                success=True,
                message_id=message_id,
                status="sent",
                recipient=to_email,
            )
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to_email, exc)
            return EmailResult(
                success=False,
                status="failed",
                error_message=str(exc),
                recipient=to_email,
            )
