import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from outreach_tool.apis.brevo import BrevoClient, EmailResult

@pytest.mark.asyncio
async def test_brevo_send_email_success(mock_config):
    with patch("outreach_tool.apis.brevo.HTTPClient") as MockHTTPClient:
        mock_http = MockHTTPClient.return_value
        mock_http.__aenter__.return_value = mock_http
        
        # Mock request response
        mock_response = MagicMock()
        mock_response.json.return_value = {"messageId": "msg-123"}
        mock_http.request = AsyncMock(return_value=mock_response)
        
        async with BrevoClient(api_key="test") as client:
            result = await client.send_email(
                to_email="to@example.com",
                from_email="from@example.com",
                subject="Test",
                html_content="<p>Hello</p>"
            )
            
            assert result.success is True
            assert result.message_id == "msg-123"
            
            mock_http.request.assert_called_once()
            args, kwargs = mock_http.request.call_args
            assert kwargs["json_data"]["to"][0]["email"] == "to@example.com"
            assert kwargs["json_data"]["subject"] == "Test"

@pytest.mark.asyncio
async def test_brevo_send_email_failure(mock_config):
    with patch("outreach_tool.apis.brevo.HTTPClient") as MockHTTPClient:
        mock_http = MockHTTPClient.return_value
        mock_http.__aenter__.return_value = mock_http
        
        mock_http.request = AsyncMock(side_effect=Exception("API Error"))
        
        async with BrevoClient(api_key="test") as client:
            result = await client.send_email(
                to_email="to@example.com",
                from_email="from@example.com",
                subject="Test"
            )
            
            assert result.success is False
            assert "API Error" in result.error_message
