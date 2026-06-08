import pytest
from outreach_tool.utils.safety import SafetyCheckpoint, SafetyStatus

def test_safety_checkpoint_initialization():
    checkpoint = SafetyCheckpoint(max_daily_emails=10, max_domain_emails=2)
    assert checkpoint.max_daily_emails == 10
    assert checkpoint.max_domain_emails == 2
    assert checkpoint.daily_count == 0

def test_safety_checkpoint_blocklist():
    checkpoint = SafetyCheckpoint(blocklist={"blocked.com"})
    
    # Blocked domain
    status = checkpoint.check_email_validity("test@blocked.com")
    assert status.passed is False
    assert "blocklist" in status.message
    
    # Allowed domain
    status = checkpoint.check_email_validity("test@allowed.com")
    assert status.passed is True

def test_safety_checkpoint_daily_limit():
    checkpoint = SafetyCheckpoint(max_daily_emails=2)
    
    checkpoint.record_email("1@test.com")
    checkpoint.record_email("2@test.com")
    
    status = checkpoint.check_email_validity("3@test.com")
    assert status.passed is False
    assert "Daily email limit" in status.message

def test_safety_checkpoint_domain_limit():
    checkpoint = SafetyCheckpoint(max_domain_emails=2)
    
    checkpoint.record_email("1@test.com")
    checkpoint.record_email("2@test.com")
    
    status = checkpoint.check_email_validity("3@test.com")
    assert status.passed is False
    assert "reached its email limit" in status.message
    
    # Different domain should pass
    status = checkpoint.check_email_validity("1@other.com")
    assert status.passed is True

def test_safety_checkpoint_record_email():
    checkpoint = SafetyCheckpoint()
    checkpoint.record_email("test@example.com", company_domain="example.com")
    
    assert checkpoint.daily_count == 1
    assert checkpoint.domain_counts["example.com"] == 1

def test_safety_checkpoint_reset_daily_count():
    from datetime import datetime, timedelta, timezone
    checkpoint = SafetyCheckpoint()
    checkpoint.daily_count = 5
    checkpoint.domain_counts = {"test.com": 5}
    
    # Backdate start_of_day
    checkpoint.start_of_day = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    
    checkpoint.reset_daily_count()
    assert checkpoint.daily_count == 0
    assert len(checkpoint.domain_counts) == 0
