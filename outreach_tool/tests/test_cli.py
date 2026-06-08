"""Tests for the CLI module and entry point."""
from __future__ import annotations

import argparse
import runpy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from outreach_tool.cli import create_parser, main, _resolve_seed_domain


# ---------------------------------------------------------------------------
# create_parser tests
# ---------------------------------------------------------------------------

def test_create_parser_positional_seed_domain() -> None:
    """Parser accepts seed domain as positional argument."""
    parser = create_parser()
    args = parser.parse_args(["acme.com"])
    assert args.seed_domain == "acme.com"
    assert args.seed_domain_flag is None


def test_create_parser_flag_seed_domain() -> None:
    """Parser accepts seed domain via --seed-domain flag."""
    parser = create_parser()
    args = parser.parse_args(
        ["--seed-domain", "acme.com"],
    )
    assert args.seed_domain is None
    assert args.seed_domain_flag == "acme.com"


def test_create_parser_all_optional_args() -> None:
    """Test all optional arguments including email overrides are accepted."""
    parser = create_parser()
    args = parser.parse_args(
        [
            "acme.com",
            "--email-subject",
            "Hello",
            "--email-html",
            "<p>Hi</p>",
            "--from-email",
            "me@example.com",
            "--from-name",
            "Sender",
            "--to-name",
            "Recipient",
            "--job-title",
            "CEO",
            "--seniority",
            "c-level",
            "--department",
            "sales",
            "--max-companies",
            "10",
            "--max-contacts",
            "5",
            "--output-dir",
            "/tmp/out",
            "--log-level",
            "DEBUG",
            "--json-logs",
        ],
    )
    assert args.seed_domain == "acme.com"
    assert args.email_subject == "Hello"
    assert args.email_html == "<p>Hi</p>"
    assert args.from_email == "me@example.com"
    assert args.from_name == "Sender"
    assert args.to_name == "Recipient"
    assert args.job_title == "CEO"
    assert args.seniority == "c-level"
    assert args.department == "sales"
    assert args.max_companies == 10
    assert args.max_contacts == 5
    assert args.output_dir == "/tmp/out"
    assert args.log_level == "DEBUG"
    assert args.json_logs is True


def test_create_parser_email_args_optional() -> None:
    """Email args are not required — parser accepts only seed domain."""
    parser = create_parser()
    # Only seed domain as positional
    args = parser.parse_args(["example.com"])
    assert args.seed_domain == "example.com"
    assert args.email_subject is None
    assert args.email_html is None
    assert args.from_email is None
    assert args.from_name is None


# ---------------------------------------------------------------------------
# _resolve_seed_domain tests
# ---------------------------------------------------------------------------

def test_resolve_seed_domain_positional() -> None:
    ns = argparse.Namespace(seed_domain="acme.com", seed_domain_flag=None)
    assert _resolve_seed_domain(ns) == "acme.com"


def test_resolve_seed_domain_flag() -> None:
    ns = argparse.Namespace(seed_domain=None, seed_domain_flag="acme.com")
    assert _resolve_seed_domain(ns) == "acme.com"


def test_resolve_seed_domain_both_prefers_positional() -> None:
    """If both are given, positional takes precedence."""
    ns = argparse.Namespace(seed_domain="pos.com", seed_domain_flag="flag.com")
    assert _resolve_seed_domain(ns) == "pos.com"


def test_resolve_seed_domain_missing() -> None:
    ns = argparse.Namespace(seed_domain=None, seed_domain_flag=None)
    with pytest.raises(SystemExit):
        _resolve_seed_domain(ns)


# ---------------------------------------------------------------------------
# async_main tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_main(mock_config) -> None:  # noqa: ANN001
    """Test the async main function with mocked orchestrator."""
    from argparse import Namespace
    from outreach_tool.cli import async_main

    args = Namespace(
        seed_domain="acme.com",
        seed_domain_flag=None,
        email_subject=None,
        email_html=None,
        from_email=None,
        from_name=None,
        to_name=None,
        job_title=None,
        seniority=None,
        department=None,
        max_companies=None,
        max_contacts=None,
        output_dir=None,
        log_level="INFO",
        json_logs=False,
    )

    mock_orchestrator = MagicMock()
    result_data = {
        "run_id": "cli-acme",
        "statistics": {
            "companies_found": 1,
            "contacts_found": 2,
            "contacts_enriched": 2,
            "emails_sent": 2,
            "emails_failed": 0,
            "contacts_skipped_dedup": 0,
            "contacts_skipped_safety": 0,
            "duration_seconds": 1.5,
        },
    }
    mock_orchestrator.run = AsyncMock(return_value=result_data)
    mock_orchestrator.results.save_run_result.return_value = "/tmp/out/run.json"

    with (
        patch("outreach_tool.cli.get_config", return_value=mock_config),
        patch("outreach_tool.cli.setup_logging") as mock_setup,
        patch("outreach_tool.cli.OutreachOrchestrator", return_value=mock_orchestrator),
    ):
        ret = await async_main(args)
        assert ret == 0
        mock_setup.assert_called_once()
        # Verify config defaults were passed to orchestrator
        call_kwargs = mock_orchestrator.run.call_args.kwargs
        assert call_kwargs["seed_domain"] == "acme.com"
        assert call_kwargs["email_subject"] == mock_config.email_subject
        assert call_kwargs["email_html"] == mock_config.email_html
        assert call_kwargs["from_email"] == mock_config.from_email
        assert call_kwargs["from_name"] == (mock_config.from_name or None)


@pytest.mark.asyncio
async def test_async_main_with_overrides(mock_config) -> None:  # noqa: ANN001
    """Test that CLI flags override config defaults."""
    from argparse import Namespace
    from outreach_tool.cli import async_main

    args = Namespace(
        seed_domain="example.com",
        seed_domain_flag=None,
        email_subject="Custom Subject",
        email_html="<p>Custom</p>",
        from_email="custom@example.com",
        from_name="Custom Sender",
        to_name=None,
        job_title=None,
        seniority=None,
        department=None,
        max_companies=None,
        max_contacts=None,
        output_dir=None,
        log_level="INFO",
        json_logs=False,
    )

    mock_orchestrator = MagicMock()
    mock_orchestrator.run = AsyncMock(return_value={
        "run_id": "cli-example",
        "statistics": {
            "companies_found": 1,
            "contacts_found": 2,
            "contacts_enriched": 2,
            "emails_sent": 2,
            "emails_failed": 0,
            "contacts_skipped_dedup": 0,
            "contacts_skipped_safety": 0,
            "duration_seconds": 1.5,
        },
    })
    mock_orchestrator.results.save_run_result.return_value = "/tmp/out/run.json"

    with (
        patch("outreach_tool.cli.get_config", return_value=mock_config),
        patch("outreach_tool.cli.setup_logging"),
        patch("outreach_tool.cli.OutreachOrchestrator", return_value=mock_orchestrator),
    ):
        ret = await async_main(args)
        assert ret == 0
        call_kwargs = mock_orchestrator.run.call_args.kwargs
        assert call_kwargs["email_subject"] == "Custom Subject"
        assert call_kwargs["email_html"] == "<p>Custom</p>"
        assert call_kwargs["from_email"] == "custom@example.com"
        assert call_kwargs["from_name"] == "Custom Sender"


@pytest.mark.asyncio
async def test_async_main_no_email_args(mock_config) -> None:
    """Test that missing email args in CLI doesn't fail, using config defaults."""
    from argparse import Namespace
    from outreach_tool.cli import async_main

    args = Namespace(
        seed_domain="noemail.com",
        seed_domain_flag=None,
        email_subject=None,
        email_html=None,
        from_email=None,
        from_name=None,
        to_name=None,
        job_title=None,
        seniority=None,
        department=None,
        max_companies=None,
        max_contacts=None,
        output_dir=None,
        log_level="INFO",
        json_logs=False,
    )

    mock_orchestrator = MagicMock()
    mock_orchestrator.run = AsyncMock(return_value={
        "run_id": "cli-noemail",
        "statistics": {
            "companies_found": 0,
            "contacts_found": 0,
            "contacts_enriched": 0,
            "emails_sent": 0,
            "emails_failed": 0,
            "contacts_skipped_dedup": 0,
            "contacts_skipped_safety": 0,
            "duration_seconds": 0.1,
        },
    })
    mock_orchestrator.results.save_run_result.return_value = "/tmp/out/run.json"

    with (
        patch("outreach_tool.cli.get_config", return_value=mock_config),
        patch("outreach_tool.cli.setup_logging"),
        patch("outreach_tool.cli.OutreachOrchestrator", return_value=mock_orchestrator),
    ):
        ret = await async_main(args)
        assert ret == 0
        call_kwargs = mock_orchestrator.run.call_args.kwargs
        assert call_kwargs["from_email"] == mock_config.from_email
        assert call_kwargs["email_subject"] == mock_config.email_subject


# ---------------------------------------------------------------------------
# main entry point tests
# ---------------------------------------------------------------------------

def test_main() -> None:
    """Test that main parses args and delegates to async_main."""

    async def _mock_async(*args, **kwargs) -> int:  # noqa: ANN002, ANN003, ARG001
        return 0

    with (
        patch("outreach_tool.cli.async_main", side_effect=_mock_async),
        patch(
            "sys.argv",
            [
                "outreach",
                "acme.com",
            ],
        ),
    ):
        ret = main()
        assert ret == 0


def test_main_with_flag() -> None:
    """Test that main works with --seed-domain flag."""

    async def _mock_async(*args, **kwargs) -> int:  # noqa: ANN002, ANN003, ARG001
        return 0

    with (
        patch("outreach_tool.cli.async_main", side_effect=_mock_async),
        patch(
            "sys.argv",
            [
                "outreach",
                "--seed-domain",
                "acme.com",
            ],
        ),
    ):
        ret = main()
        assert ret == 0


def test_main_module_entry_point() -> None:
    """Test that __main__.py runs the CLI main function."""
    with (
        patch("outreach_tool.cli.main", return_value=0) as mock_main,
        pytest.raises(SystemExit) as exc_info,
    ):
        runpy.run_module("outreach_tool.__main__", run_name="__main__")
    assert exc_info.value.code == 0  # noqa: PT017
    mock_main.assert_called_once()
