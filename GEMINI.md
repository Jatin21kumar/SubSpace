# GEMINI.md - Project Architecture & Conventions

## Overview
Outreach Tool is a modular Python CLI application for automated outreach. It orchestrates finding similar companies via Ocean.io, discovering/enriching contacts via Prospeo, and sending transactional emails via Brevo.

## Architecture
- **`outreach_tool/cli.py`**: Entry point for argument parsing.
- **`outreach_tool/orchestrator.py`**: Main workflow controller.
- **`outreach_tool/core/`**: Infrastructure components (config, http client, logging).
- **`outreach_tool/apis/`**: Service-specific API clients.
- **`outreach_tool/utils/`**: Shared utilities for deduplication, safety, and output.

## Technical Conventions
- **Shared HTTP Client**: All API clients MUST use the `HTTPClient` from `core/http_client.py` to ensure consistent rate limiting, timeouts, and retry behavior.
- **Data Persistence**: Run results and statistics are persisted as JSON files in a dedicated output directory (managed by `utils/output.py`).
- **Safety First**: The orchestrator must run safety checks (blocklists, daily caps) via `utils/safety.py` before any email is sent.
- **Deduplication**: Email addresses must be checked against the persistent deduplication store in `utils/dedup.py`.

## Workflows
- **Outreach Loop**: Seed Domain -> Ocean.io -> Prospeo (Search) -> Prospeo (Enrich) -> Safety/Deduplication -> Brevo.
- **Error Handling**: API errors should be handled gracefully with retries where appropriate, and logged with sufficient context for debugging.
