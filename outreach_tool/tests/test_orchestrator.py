import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from outreach_tool.orchestrator import OutreachOrchestrator, OutreachContact
from outreach_tool.apis.oceanio import Company
from outreach_tool.apis.prospeo import PersonProfile, EnrichedProfile
from outreach_tool.apis.brevo import EmailResult

@pytest.mark.asyncio
async def test_orchestrator_full_workflow(mock_config):
    # Mock OceanIO
    mock_ocean_instance = AsyncMock()
    mock_ocean_instance.__aenter__.return_value = mock_ocean_instance
    mock_ocean_instance.find_similar_companies.return_value = [
        Company(name="Acme Corp", domain="acme.com")
    ]
    
    # Mock Prospeo
    mock_prospeo_instance = AsyncMock()
    mock_prospeo_instance.__aenter__.return_value = mock_prospeo_instance
    mock_prospeo_instance.search_persons.return_value = [
        PersonProfile(first_name="Alice", last_name="Smith", email="alice@acme.com", title="CEO")
    ]
    mock_prospeo_instance.enrich_person.return_value = EnrichedProfile(
        first_name="Alice", last_name="Smith", email="alice@acme.com", title="CEO", seniority="c-level"
    )
    
    # Mock Brevo
    mock_brevo_instance = AsyncMock()
    mock_brevo_instance.__aenter__.return_value = mock_brevo_instance
    mock_brevo_instance.send_email.return_value = EmailResult(success=True, message_id="msg-1")

    with patch("outreach_tool.orchestrator.OceanIOClient", return_value=mock_ocean_instance), \
         patch("outreach_tool.orchestrator.ProspeoClient", return_value=mock_prospeo_instance), \
         patch("outreach_tool.orchestrator.BrevoClient", return_value=mock_brevo_instance), \
         patch("builtins.input", return_value="y"):
        
        orchestrator = OutreachOrchestrator()
        result = await orchestrator.run(
            seed_domain="seed.com",
            email_subject="Hello",
            email_html="Hi {{first_name}}",
            from_email="me@me.com"
        )
        
        assert result["statistics"]["emails_sent"] == 1
        assert len(result["contacts"]) == 1
        assert result["contacts"][0]["status"] == "sent"
        
        mock_brevo_instance.send_email.assert_called_once()
        args, kwargs = mock_brevo_instance.send_email.call_args
        assert kwargs["to_email"] == "alice@acme.com"
        assert "Alice" in kwargs["html_content"]

@pytest.mark.asyncio
async def test_orchestrator_deduplication(mock_config):
    orchestrator = OutreachOrchestrator()
    # Pre-populate dedup store
    orchestrator.dedup.add("duplicate@example.com")
    
    mock_ocean_instance = AsyncMock()
    mock_ocean_instance.__aenter__.return_value = mock_ocean_instance
    mock_ocean_instance.find_similar_companies.return_value = [
        Company(name="Dup Corp", domain="example.com")
    ]
    
    mock_prospeo_instance = AsyncMock()
    mock_prospeo_instance.__aenter__.return_value = mock_prospeo_instance
    mock_prospeo_instance.search_persons.return_value = [
        PersonProfile(first_name="Dup", last_name="User", email="duplicate@example.com")
    ]
    
    with patch("outreach_tool.orchestrator.OceanIOClient", return_value=mock_ocean_instance), \
         patch("outreach_tool.orchestrator.ProspeoClient", return_value=mock_prospeo_instance), \
         patch("outreach_tool.orchestrator.BrevoClient", return_value=AsyncMock()), \
         patch("builtins.input", return_value="y"):
        
        result = await orchestrator.run(
            seed_domain="seed.com",
            email_subject="Hello",
            email_html="Hi",
            from_email="me@me.com"
        )
        
        assert orchestrator.stats.contacts_skipped_dedup == 1
        assert orchestrator.stats.emails_sent == 0

@pytest.mark.asyncio
async def test_orchestrator_safety_skip(mock_config):
    orchestrator = OutreachOrchestrator()
    # Mock safety checkpoint to fail
    with patch.object(orchestrator.safety, "check_email_validity") as mock_check:
        from outreach_tool.utils.safety import SafetyStatus
        mock_check.return_value = SafetyStatus(passed=False, message="Safety blocked")
        
        mock_ocean_instance = AsyncMock()
        mock_ocean_instance.__aenter__.return_value = mock_ocean_instance
        mock_ocean_instance.find_similar_companies.return_value = [
            Company(name="Safe Corp", domain="safe.com")
        ]
        
        mock_prospeo_instance = AsyncMock()
        mock_prospeo_instance.__aenter__.return_value = mock_prospeo_instance
        mock_prospeo_instance.search_persons.return_value = [
            PersonProfile(first_name="Safe", last_name="User", email="blocked@safe.com")
        ]
        
        with patch("outreach_tool.orchestrator.OceanIOClient", return_value=mock_ocean_instance), \
             patch("outreach_tool.orchestrator.ProspeoClient", return_value=mock_prospeo_instance), \
             patch("outreach_tool.orchestrator.BrevoClient", return_value=AsyncMock()), \
             patch("builtins.input", return_value="y"):
            
            result = await orchestrator.run(
                seed_domain="seed.com",
                email_subject="Hello",
                email_html="Hi",
                from_email="me@me.com"
            )
            
            assert orchestrator.stats.contacts_skipped_safety == 1

@pytest.mark.asyncio
async def test_orchestrator_user_abort(mock_config):
    mock_ocean_instance = AsyncMock()
    mock_ocean_instance.__aenter__.return_value = mock_ocean_instance
    mock_ocean_instance.find_similar_companies.return_value = [Company(name="A", domain="a.com")]
    
    mock_prospeo_instance = AsyncMock()
    mock_prospeo_instance.__aenter__.return_value = mock_prospeo_instance
    mock_prospeo_instance.search_persons.return_value = [PersonProfile(email="test@a.com")]
    mock_prospeo_instance.enrich_person.return_value = None

    with patch("outreach_tool.orchestrator.OceanIOClient", return_value=mock_ocean_instance), \
         patch("outreach_tool.orchestrator.ProspeoClient", return_value=mock_prospeo_instance), \
         patch("outreach_tool.orchestrator.BrevoClient", return_value=AsyncMock()), \
         patch("builtins.input", return_value="n"): # User says NO
        
        orchestrator = OutreachOrchestrator()
        result = await orchestrator.run(
            seed_domain="seed.com",
            email_subject="Hello",
            email_html="Hi",
            from_email="me@me.com"
        )
        
        assert result["statistics"]["emails_sent"] == 0
        assert orchestrator.stats.contacts_found == 1
