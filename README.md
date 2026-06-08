# Outreach Tool

An end-to-end Python CLI application for automated outreach: find similar companies, discover contacts, enrich profiles, and send emails.

## Architecture

```
outreach_tool/
├── __init__.py            # Package version
├── __main__.py            # Entry point: `python -m outreach_tool`
├── cli.py                 # CLI argument parsing with argparse
├── orchestrator.py        # Workflow orchestrator
├── core/
│   ├── config.py          # Pydantic settings from environment
│   ├── http_client.py     # Shared async HTTP client with retries
│   └── logging_config.py  # Structured (JSON) logging
├── apis/
│   ├── oceanio.py         # Ocean.io API: find similar companies
│   ├── prospeo.py         # Prospeo API: search & enrich persons
│   └── brevo.py           # Brevo API: send transactional emails
└── utils/
    ├── dedup.py           # Email deduplication with JSON persistence
    ├── output.py          # Results & statistics persistence
    └── safety.py          # Rate limits, blocklists, safety checks
```

## Workflow

1. **Seed Domain** → User provides a starting company domain
2. **Ocean.io** → Find similar companies
3. **Prospeo** → Search for persons at each company
4. **Prospeo** → Enrich each person's profile
5. **Safety Checkpoint** → Validate sending limits and blocklists
6. **Brevo** → Send personalized emails
7. **Save Results** → Persist run data and statistics to JSON

## Installation

```bash
pip install -r requirements.txt
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

## Usage

### Basic

```bash
outreach \
  --seed-domain "acme.com" \
  --email-subject "Collaboration Opportunity" \
  --email-html "<p>Hi, I'd love to connect!</p>" \
  --from-email "me@example.com"
```

### With Filters

```bash
outreach \
  --seed-domain "techcorp.io" \
  --email-subject "Partnership Inquiry" \
  --email-html "<p>Hello</p>" \
  --from-email "jane@example.com" \
  --job-title "CTO" \
  --seniority "c-level" \
  --max-companies 50
```

## Required API Keys

| Service | API Key | Endpoint |
|---------|---------|----------|
| Ocean.io | `OCEAN_API_KEY` | `/companies/similar` |
| Prospeo | `PROSPEO_API_KEY` | `/search-person`, `/enrich-person` |
| Brevo | `BREVO_API_KEY` | `/smtp/email` |

## Features

- **Modular Architecture** – API clients, utilities, and orchestrator are cleanly separated
- **Shared HTTP Client** – Centralized `HTTPClient` with configurable rate limiting, exponential backoff, and retries
- **Pagination Support** – Built-in paginated request handling across all APIs
- **Retry with Exponential Backoff** – Powered by `tenacity` for resilient API calls
- **Structured Logging** – JSON or plain text logs with consistent formatting
- **Email Deduplication** – Persistent JSON store with configurable retention window
- **Company/Contact Limits** – Configurable caps to control API usage and costs
- **JSON Output** – Every run saves results and statistics to JSON files
- **Final Statistics** – Console summary showing processing metrics
- **Safety Checkpoints** – Domain blocklists, rate limiting, and daily send caps
