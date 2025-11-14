# Technical Stack

## Build System & Package Management

- **Package Manager**: UV (modern Python packaging)
- **Build Backend**: Hatchling
- **Python Version**: 3.10+ (3.13+ recommended for optimal performance)

## Core Technologies

### Framework & Server
- **FastMCP**: MCP server framework (0.2.0+)
- **Uvicorn**: ASGI server for HTTP mode
- **asyncio**: Async/await architecture throughout

### Data Processing
- **pandas**: DataFrame operations and financial data manipulation (2.2.0+)
- **numpy**: Numerical computations (1.26.0+)
- **yfinance**: Yahoo Finance API client (0.2.28+)

### HTTP & Networking
- **httpx**: Modern async HTTP client (0.27.0+)
- **aiohttp**: Additional async HTTP support (3.9.0+)
- **aiofiles**: Async file operations (24.1.0+)

### Data Sources
- **beautifulsoup4** + **lxml**: HTML/XML parsing for SEC filings
- **pytrends**: Google Trends API client (4.9.0+)
- **feedparser**: RSS feed parsing for news (6.0.0+)

### Utilities
- **cachetools**: In-memory caching (5.3.0+)
- **asyncio-throttle**: Rate limiting (1.0.2+)
- **python-dotenv**: Environment configuration (1.0.0+)

## Development Tools

### Testing
- **pytest**: Test framework (8.0.0+)
- **pytest-asyncio**: Async test support (0.23.0+)
- **pytest-mock**: Mocking utilities (3.12.0+)
- **pytest-cov**: Coverage reporting (7.0.0+)

### Code Quality
- **black**: Code formatting (24.0.0+)
- **ruff**: Fast linting (0.4.0+)
- **mypy**: Type checking (1.10.0+)

## Common Commands

### Development Setup
```bash
# Install with development dependencies
uv sync --dev

# Install in editable mode
uv pip install -e ".[dev]"
```

### Running the Server
```bash
# Start MCP server
uv run python -m iso_financial_mcp

# Start HTTP server
uv run uvicorn iso_financial_mcp.server:server.app --host 0.0.0.0 --port 8000

# Test individual endpoint
uv run python -c "
from iso_financial_mcp.server import get_info
import asyncio
result = asyncio.run(get_info('AAPL'))
print(result)
"
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=iso_financial_mcp --cov-report=html

# Run specific test file
uv run pytest tests/test_meta_tools.py -v

# Run specific test
uv run pytest tests/test_meta_tools.py::TestUtilityFunctions::test_truncate_string_long_text -v
```

### Code Quality
```bash
# Format code
uv run black .

# Lint code
uv run ruff check . --fix

# Type check
uv run mypy .

# Run all quality checks
uv run black . && uv run ruff check . && uv run mypy .
```

### Building & Publishing
```bash
# Build package
uv build

# Check package
uv run twine check dist/*

# Publish to PyPI (maintainers only)
uv run twine upload dist/*
```

## Architecture Patterns

### Async/Await
All data fetching uses async/await for non-blocking I/O. Use `asyncio.gather()` for parallel execution.

### Caching Strategy
Multi-tier caching with configurable TTL per data source:
- Market data: 5 minutes
- Options: 15 minutes
- News: 2 hours
- SEC filings: 6 hours
- FINRA/Earnings/Trends: 24 hours

### Error Handling
Graceful degradation - partial failures don't break entire requests. Errors are collected and reported separately.

### Rate Limiting
Per-endpoint rate limiting with exponential backoff. Respects API provider constraints.

## Configuration

### Environment Variables
Optional `.env` file for advanced configuration. No API keys required - all data sources are free/public.

### Cache Configuration
Default TTL settings in `CACHE_TTL` dict. Adjust per data source as needed.

### Rate Limits
Default limits in `RATE_LIMITS` dict. Configured per API provider.
