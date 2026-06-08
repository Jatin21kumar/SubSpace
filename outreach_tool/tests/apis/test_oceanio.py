import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from outreach_tool.apis.oceanio import OceanIOClient, Company

@pytest.mark.asyncio
async def test_oceanio_find_similar_companies(mock_config):
    with patch("outreach_tool.apis.oceanio.HTTPClient") as MockHTTPClient:
        mock_http = MockHTTPClient.return_value
        mock_http.__aenter__.return_value = mock_http
        
        # Mock response from POST /search/companies with nested company object
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "companies": [
                {
                    "company": {
                        "name": "Company A",
                        "domain": "a.com",
                        "industries": ["Tech"],
                        "companySize": "51-200",
                        "primaryCountry": "US"
                    },
                    "relevance": "A"
                },
                {
                    "company": {
                        "name": "Company B",
                        "domain": "b.com",
                        "industries": ["SaaS"],
                        "companySize": "201-500",
                        "primaryCountry": "UK"
                    },
                    "relevance": "B"
                }
            ],
            "searchAfter": None
        }
        mock_http.request = AsyncMock(return_value=mock_response)
        
        async with OceanIOClient(api_key="test") as client:
            companies = await client.find_similar_companies("example.com")
            
            assert len(companies) == 2
            assert companies[0].name == "Company A"
            assert companies[0].domain == "a.com"
            assert companies[0].industry == "Tech"
            assert companies[0].company_size == "51-200"
            assert companies[0].location == "US"
            
            assert companies[1].name == "Company B"
            assert companies[1].domain == "b.com"
            assert companies[1].location == "UK"
            
            mock_http.request.assert_called_once()
            args, kwargs = mock_http.request.call_args
            assert args[0] == "POST"
            assert args[1] == "/search/companies"
            # Corrected: lookalikeDomains is inside companiesFilters
            assert kwargs["json_data"]["companiesFilters"]["lookalikeDomains"] == ["example.com"]

@pytest.mark.asyncio
async def test_oceanio_pagination(mock_config):
    with patch("outreach_tool.apis.oceanio.HTTPClient") as MockHTTPClient:
        mock_http = MockHTTPClient.return_value
        mock_http.__aenter__.return_value = mock_http
        
        # First page response
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = {
            "companies": [{"company": {"name": "C1", "domain": "c1.com"}}],
            "searchAfter": "cursor1"
        }
        
        # Second page response
        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = {
            "companies": [{"company": {"name": "C2", "domain": "c2.com"}}],
            "searchAfter": None
        }
        
        mock_http.request = AsyncMock(side_effect=[mock_response_1, mock_response_2])
        
        async with OceanIOClient(api_key="test") as client:
            companies = await client.find_similar_companies("example.com", page_size=1, max_pages=2)
            
            assert len(companies) == 2
            assert companies[0].name == "C1"
            assert companies[1].name == "C2"
            
            assert mock_http.request.call_count == 2
            
            # Verify second call used searchAfter
            args2, kwargs2 = mock_http.request.call_args_list[1]
            assert kwargs2["json_data"]["searchAfter"] == "cursor1"
