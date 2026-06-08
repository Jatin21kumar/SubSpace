import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from outreach_tool.apis.prospeo import ProspeoClient, PersonProfile, EnrichedProfile

@pytest.mark.asyncio
async def test_prospeo_search_persons(mock_config):
    with patch("outreach_tool.apis.prospeo.HTTPClient") as MockHTTPClient:
        mock_http = MockHTTPClient.return_value
        mock_http.__aenter__.return_value = mock_http
        
        # Mock request response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"person": {"first_name": "John", "last_name": "Doe", "email": "john@a.com", "job_title": "CEO"}}
            ],
            "pagination": {"total_page": 1, "current_page": 1}
        }
        mock_http.request = AsyncMock(return_value=mock_response)
        
        async with ProspeoClient(api_key="test") as client:
            persons = await client.search_persons("a.com")
            
            assert len(persons) == 1
            assert persons[0].first_name == "John"
            assert persons[0].email == "john@a.com"
            
            mock_http.request.assert_called_once()

@pytest.mark.asyncio
async def test_prospeo_enrich_person(mock_config):
    with patch("outreach_tool.apis.prospeo.HTTPClient") as MockHTTPClient:
        mock_http = MockHTTPClient.return_value
        mock_http.__aenter__.return_value = mock_http
        
        # Mock request response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "contact": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@a.com",
                "job_title": "CEO",
                "seniority": "c-level"
            }
        }
        mock_http.request = AsyncMock(return_value=mock_response)
        
        async with ProspeoClient(api_key="test") as client:
            enriched = await client.enrich_person(email="john@a.com")
            
            assert enriched is not None
            assert enriched.first_name == "John"
            assert enriched.seniority == "c-level"
            
            mock_http.request.assert_called_once()
            args, kwargs = mock_http.request.call_args
            assert kwargs["json_data"]["email"] == "john@a.com"
