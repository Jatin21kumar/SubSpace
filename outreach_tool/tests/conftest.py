import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from outreach_tool.core.config import Config

@pytest.fixture
def mock_config(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    config = Config(
        ocean_api_key="test_ocean_key",
        prospeo_api_key="test_prospeo_key",
        brevo_api_key="test_brevo_key",
        from_email="test@example.com",
        from_name="Test Sender",
        email_subject="Test Subject",
        email_html="<p>Hi {{first_name}}</p>",
        output_dir=output_dir,
        requests_per_second=100.0, # Fast tests
        max_retries=1
    )
    with patch("outreach_tool.core.config.get_config", return_value=config):
        yield config

@pytest.fixture
def temp_output_dir(tmp_path):
    d = tmp_path / "outreach_results"
    d.mkdir()
    return d
