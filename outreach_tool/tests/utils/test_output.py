import json
import pytest
from pathlib import Path
from outreach_tool.utils.output import RunResults, RunStatistics

def test_run_statistics():
    stats = RunStatistics(run_id="test_run")
    stats.companies_found = 10
    stats.emails_sent = 5
    
    d = stats.to_dict()
    assert d["run_id"] == "test_run"
    assert d["companies_found"] == 10
    assert d["emails_sent"] == 5
    assert "started_at" in d

def test_run_results_save(tmp_path):
    results = RunResults(tmp_path)
    data = {"key": "value"}
    
    filepath = results.save_run_result("test_run", data)
    assert filepath.exists()
    
    with open(filepath, "r") as f:
        loaded = json.load(f)
    assert loaded == data

def test_run_results_save_statistics(tmp_path):
    results = RunResults(tmp_path)
    stats = RunStatistics(run_id="test_run")
    
    filepath = results.save_statistics(stats)
    assert filepath.exists()
    assert f"stats_{stats.run_id}.json" in filepath.name
