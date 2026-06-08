# CLAUDE.md - Outreach Tool Instructions

## Build and Setup
- Install dependencies: `pip install -r requirements.txt`
- Install dev dependencies: `pip install -e ".[dev]"`
- Configuration: Copy `.env.example` to `.env` and provide API keys.

## Development Commands
- **Run CLI**: `python -m outreach_tool` or `outreach [args]`
- **Linting**: `ruff check .`
- **Formatting**: `ruff format .`
- **Type Checking**: `mypy .`
- **Testing**: `pytest`

## Code Style & Conventions
- **Version**: Python 3.12+
- **Style**: Adhere to `ruff` rules (Google docstring convention, 120 line length).
- **Typing**: Strict type hints required (`mypy --strict`).
- **Configuration**: Use `pydantic-settings` for environment variables in `outreach_tool/core/config.py`.
- **Async**: Use `httpx` for asynchronous HTTP requests.
- **Resilience**: Use `tenacity` for retry logic on API calls.
- **Logging**: Use structured JSON logging provided by `outreach_tool/core/logging_config.py`.
