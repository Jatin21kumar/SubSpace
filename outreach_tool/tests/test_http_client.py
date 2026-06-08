import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from outreach_tool.core.http_client import HTTPClient, APIError

@pytest.mark.asyncio
async def test_http_client_429_quota_logging(mock_config):
    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient.request") as mock_request:
        # Create a mock response with 429 and quota headers
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.text = '{"error": "rate limit"}'
        mock_response.headers = httpx.Headers({
            "x-daily-request-left": "0",
            "x-daily-reset-seconds": "3600",
            "Content-Type": "application/json"
        })
        # Mock raise_for_status to raise the expected error
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limit", request=MagicMock(), response=mock_response
        )
        
        mock_request.return_value = mock_response

        # Use HTTPClient with 1 retry to avoid long test
        async with HTTPClient(base_url="https://api.test", max_retries=1, config=mock_config) as client:
            with pytest.raises(APIError) as exc_info:
                await client.request("GET", "/test")
            
            assert "x-daily-request-left: 0" in str(exc_info.value)
            assert "x-daily-reset-seconds: 3600" in str(exc_info.value)
            assert exc_info.value.status_code == 429
