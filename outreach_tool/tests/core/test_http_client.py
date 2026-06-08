import pytest
import httpx
from unittest.mock import MagicMock, patch
from outreach_tool.core.http_client import HTTPClient, APIError

@pytest.mark.asyncio
async def test_http_client_429_quota_logging(mock_config):
    """Test that 429 errors capture quota/rate-limit headers in the exception message."""
    # Mock httpx.AsyncClient.request
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
            
            error_msg = str(exc_info.value)
            assert "x-daily-request-left: 0" in error_msg
            assert "x-daily-reset-seconds: 3600" in error_msg
            assert exc_info.value.status_code == 429

@pytest.mark.asyncio
async def test_http_client_no_retry_on_400(mock_config):
    """Test that 400 series errors (non-retryable) are not retried."""
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = '{"error": "Field required"}'
        mock_response.headers = httpx.Headers({})
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        
        mock_request.return_value = mock_response

        # Use HTTPClient with multiple retries configured - should still only call once
        async with HTTPClient(base_url="https://api.test", max_retries=5, config=mock_config) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.request("POST", "/test")
            
            # Should only be called once because 400 is not in retry_statuses
            assert mock_request.call_count == 1
