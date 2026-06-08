"""CLI entry point for the outreach automation tool."""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from outreach_tool.core.config import get_config
from outreach_tool.core.logging_config import setup_logging
from outreach_tool.orchestrator import OutreachOrchestrator
from outreach_tool.utils.console import console


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="outreach",
        description="Automated end-to-end outreach pipeline. Provide a seed domain to automatically find similar companies, enrich contacts, and send emails.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The pipeline runs end-to-end automatically:
  1. Search Ocean.io for companies similar to the seed domain
  2. Find persons at each company using Prospeo
  3. Enrich each person's profile with Prospeo
  4. Run safety and deduplication checks
  5. Send emails via Brevo

Examples:
  %(prog)s company.com
  %(prog)s --seed-domain "acme.com" --max-companies 50
        """,
    )

    # Seed domain: required positional or --seed-domain flag
    parser.add_argument(
        "seed_domain",
        nargs="?",
        help="REQUIRED: Seed company domain (e.g., 'acme.com') for finding similar companies.",
    )
    parser.add_argument(
        "--seed-domain",
        dest="seed_domain_flag",
        default=None,
        help="Seed company domain (alternative to positional arg).",
    )

    # Optional overrides from config defaults
    parser.add_argument(
        "--email-subject",
        dest="email_subject",
        default=None,
        help="Subject line for the outreach email.",
    )
    parser.add_argument(
        "--email-html",
        dest="email_html",
        default=None,
        help="HTML content of the outreach email.",
    )
    parser.add_argument(
        "--from-email",
        dest="from_email",
        default=None,
        help="Sender email address.",
    )
    parser.add_argument(
        "--from-name",
        dest="from_name",
        default=None,
        help="Sender display name.",
    )

    # Optional arguments
    parser.add_argument(
        "--to-name",
        dest="to_name",
        default=None,
        help="Recipient display name (overrides individual contact names).",
    )
    parser.add_argument(
        "--job-title",
        dest="job_title",
        default=None,
        help="Filter contacts by job title (Prospeo search filter).",
    )
    parser.add_argument(
        "--seniority",
        dest="seniority",
        default=None,
        help="Filter contacts by seniority (e.g., 'director', 'vp', 'c-level').",
    )
    parser.add_argument(
        "--department",
        dest="department",
        default=None,
        help="Filter contacts by department (e.g., 'sales', 'marketing').",
    )
    parser.add_argument(
        "--max-companies",
        dest="max_companies",
        type=int,
        default=None,
        help="Maximum number of similar companies to process (default: from config).",
    )
    parser.add_argument(
        "--max-contacts",
        dest="max_contacts",
        type=int,
        default=None,
        help="Maximum contacts per company (default: from config).",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Directory for output files (default: from config).",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO).",
    )
    parser.add_argument(
        "--json-logs",
        dest="json_logs",
        action="store_true",
        help="Format logs as JSON.",
    )

    return parser


def _resolve_seed_domain(args: argparse.Namespace) -> str:
    """Resolve seed domain from positional or flag argument."""
    seed_domain = args.seed_domain or args.seed_domain_flag
    if not seed_domain:
        raise SystemExit("Error: seed domain is required. Usage: outreach <domain>")
    return seed_domain


def _resolve_email_args(args: argparse.Namespace, config: Any) -> dict[str, str]:
    """Resolve email-related arguments, preferring CLI overrides over config defaults."""
    return {
        "email_subject": args.email_subject or config.email_subject,
        "email_html": args.email_html or config.email_html,
        "from_email": args.from_email or config.from_email,
        "from_name": args.from_name or config.from_name,
    }


async def async_main(args: argparse.Namespace) -> int:
    """Run the main async workflow."""
    config = get_config()

    # Resolve seed domain
    seed_domain = _resolve_seed_domain(args)

    # Resolve email args (CLI overrides config defaults)
    email_args = _resolve_email_args(args, config)

    setup_logging(
        level=args.log_level,
        log_file=config.output_dir / "outreach.log",
        json_output=args.json_logs,
    )

    orchestrator = OutreachOrchestrator(
        run_id="cli-" + seed_domain.split(".")[0],
        max_companies=args.max_companies,
        max_contacts_per_company=args.max_contacts,
        output_dir=args.output_dir,
    )

    result = await orchestrator.run(
        seed_domain=seed_domain,
        email_subject=email_args["email_subject"],
        email_html=email_args["email_html"],
        from_email=email_args["from_email"],
        from_name=email_args["from_name"],
        to_name=args.to_name,
        job_title_filter=args.job_title,
        seniority_filter=args.seniority,
        department_filter=args.department,
    )

    # Save results to JSON
    output_path = orchestrator.results.save_run_result(result["run_id"], result)
    orchestrator.results.save_statistics(orchestrator.stats)

    # Print summary to console
    console.final_summary(
        seed_domain=seed_domain,
        stats=result["statistics"],
        output_file=str(output_path),
    )

    return 0


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())
