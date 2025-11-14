# Project Structure

## Directory Organization

```
iso-financial-mcp/
├── iso_financial_mcp/          # Main package
│   ├── __init__.py              # Package initialization, version info
│   ├── __main__.py              # Entry point for python -m execution
│   ├── server.py                # FastMCP server with tool definitions
│   ├── main.py                  # Alternative entry point
│   ├── run_mcp.py               # MCP runner utilities
│   ├── meta_tools.py            # Consolidated meta-tools (NEW in 0.3.0)
│   └── datasources/             # Data source modules
│       ├── __init__.py
│       ├── yfinance_source.py   # Yahoo Finance integration
│       ├── sec_source.py        # SEC EDGAR API
│       ├── finra_source.py      # FINRA short volume
│       ├── earnings_source.py   # Earnings calendar
│       ├── news_source.py       # RSS news feeds
│       ├── trends_source.py     # Google Trends
│       └── validation.py        # Input validation utilities
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_meta_tools.py       # Meta-tools tests (NEW in 0.3.0)
│   ├── test_format_simple.py    # Formatting tests
│   └── README.md                # Testing documentation
├── .kiro/                       # Kiro IDE configuration
│   ├── steering/                # AI assistant guidance (this folder)
│   └── specs/                   # Feature specifications
├── dist/                        # Build artifacts (generated)
├── .venv/                       # Virtual environment (generated)
├── pyproject.toml               # Project metadata and dependencies
├── uv.lock                      # UV lock file
├── README.md                    # Main documentation
├── CHANGELOG.md                 # Version history
├── MIGRATION_GUIDE.md           # Migration from individual tools to meta-tools
├── LICENSE                      # MIT License
└── .gitignore                   # Git ignore rules
```

## Module Responsibilities

### `server.py` (779 lines)
- FastMCP server instantiation
- Tool definitions with `@server.tool` decorator
- **Meta-tools**: `get_ticker_complete_analysis`, `get_multi_ticker_analysis`, `analyze_sector_companies`
- **Legacy tools**: Individual data source endpoints (maintained for backward compatibility)
- Helper functions: `dataframe_to_string()`
- Server entry point: `if __name__ == "__main__": server.run()`

### `meta_tools.py` (815 lines)
- **Core functions**:
  - `get_financial_snapshot()`: Single ticker parallel data retrieval
  - `get_multi_ticker_snapshot()`: Multi-ticker parallel analysis
  - `format_snapshot_for_llm()`: Token-optimized formatting
  - `format_multi_snapshot_for_llm()`: Multi-ticker formatting
- **Utility functions**:
  - `truncate_string()`: Intelligent text truncation
  - `format_compact_data()`: Compact data structure formatting
  - `_format_data_compact()`: Internal data compaction
- Uses `asyncio.gather()` for parallel execution
- Implements graceful degradation with error collection

### `datasources/` Package
Each module follows consistent patterns:
- Async functions for data retrieval
- Caching decorators (`@cached_request`)
- Rate limiting decorators (`@rate_limit`)
- Error handling with try/except
- Returns structured data (dicts, lists, DataFrames)

**Key modules**:
- `yfinance_source.py`: Core market data, options, financials
- `sec_source.py`: SEC EDGAR API integration
- `finra_source.py`: Short volume data with trend analysis
- `earnings_source.py`: Earnings calendar with EPS data
- `news_source.py`: RSS feed parsing with deduplication
- `trends_source.py`: Google Trends with momentum analysis
- `validation.py`: Input validation and sanitization

### `tests/` Package
- **Unit tests**: Individual function testing
- **Integration tests**: Complete workflow testing
- **Performance tests**: Parallel execution benchmarks
- Test structure mirrors source structure
- Uses pytest fixtures and async test support
- Coverage target: >80%

## Code Organization Patterns

### Tool Definition Pattern
```python
@server.tool
async def tool_name(param: str) -> str:
    """
    Tool description for LLM.
    :param param: Parameter description
    """
    # Implementation
    return formatted_result
```

### Data Source Pattern
```python
@rate_limit('api_name', calls_per_minute=60)
@cached_request(ttl=3600)
async def get_data(ticker: str) -> Optional[Dict]:
    """Fetch data from source"""
    try:
        # Async HTTP request
        # Data processing
        return structured_data
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
```

### Meta-tool Pattern
```python
async def get_snapshot(ticker: str) -> Dict[str, Any]:
    """Parallel data retrieval"""
    tasks = [
        source1.get_data(ticker),
        source2.get_data(ticker),
        # ... more sources
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Process results with error handling
    return snapshot
```

## File Naming Conventions

- **Modules**: `snake_case.py` (e.g., `meta_tools.py`, `yfinance_source.py`)
- **Tests**: `test_*.py` (e.g., `test_meta_tools.py`)
- **Classes**: `PascalCase` (e.g., `TestUtilityFunctions`)
- **Functions**: `snake_case` (e.g., `get_financial_snapshot`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `CACHE_TTL`)

## Import Organization

Standard order:
1. Standard library imports
2. Third-party imports (pandas, fastmcp, etc.)
3. Local imports (relative imports from package)

Example:
```python
import asyncio
from datetime import datetime
from typing import Dict, Any

import pandas as pd
from fastmcp.server.server import FastMCP

from .datasources import yfinance_source
from .meta_tools import get_financial_snapshot
```

## Key Design Principles

1. **Async-first**: All I/O operations use async/await
2. **Parallel execution**: Use `asyncio.gather()` for concurrent operations
3. **Graceful degradation**: Partial failures don't break entire requests
4. **Token optimization**: Truncate and compact data for LLM efficiency
5. **Type hints**: Use type annotations throughout
6. **Error context**: Provide actionable error messages
7. **Backward compatibility**: Legacy tools maintained alongside meta-tools
