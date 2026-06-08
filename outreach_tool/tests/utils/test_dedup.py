import json
import pytest
from pathlib import Path
from outreach_tool.utils.dedup import DedupStore

def test_dedup_store_basic(tmp_path):
    store_path = tmp_path / "dedup.json"
    store = DedupStore(store_path)
    
    email = "test@example.com"
    assert store.is_duplicate(email) is False
    
    store.add(email)
    assert store.is_duplicate(email) is True
    
    # Case insensitive
    assert store.is_duplicate("TEST@example.com") is True

def test_dedup_store_persistence(tmp_path):
    store_path = tmp_path / "dedup.json"
    
    # Create store and add email
    with DedupStore(store_path) as store:
        store.add("test@example.com")
    
    # Check if file exists
    assert store_path.exists()
    
    # Load in new store
    store2 = DedupStore(store_path)
    assert store2.is_duplicate("test@example.com") is True

def test_dedup_store_retention(tmp_path):
    from datetime import datetime, timedelta, timezone
    store_path = tmp_path / "dedup.json"
    
    # Manually create a file with an old record
    old_date = datetime.now(timezone.utc) - timedelta(days=40)
    data = {
        "old@example.com": {"sent_at": old_date.isoformat()},
        "new@example.com": {"sent_at": datetime.now(timezone.utc).isoformat()}
    }
    store_path.write_text(json.dumps(data))
    
    store = DedupStore(store_path, retention_days=30)
    assert store.is_duplicate("old@example.com") is False
    assert store.is_duplicate("new@example.com") is True
