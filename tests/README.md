# IsoFinancial-MCP Tests

This directory contains the test suite for the IsoFinancial-MCP meta-tools optimization.

## Running Tests

### Run all tests
```bash
uv run pytest tests/ -v
```

### Run specific test file
```bash
uv run pytest tests/test_meta_tools.py -v
```

### Run specific test class
```bash
uv run pytest tests/test_meta_tools.py::TestUtilityFunctions -v
```

### Run specific test
```bash
uv run pytest tests/test_meta_tools.py::TestUtilityFunctions::test_truncate_string_short_text -v
```

### Run with coverage
```bash
uv run pytest tests/ -v --cov=iso_financial_mcp --cov-report=html
```

## Test Structure

### test_meta_tools.py
Comprehensive test suite for meta-tools module including:

- **TestUtilityFunctions**: Tests for `truncate_string()` and `format_compact_data()`
- **TestGetFinancialSnapshot**: Tests for single ticker snapshot retrieval
- **TestGetMultiTickerSnapshot**: Tests for multi-ticker parallel retrieval
- **TestFormatting**: Tests for LLM-optimized formatting functions
- **TestIntegration**: End-to-end workflow tests
- **TestEdgeCases**: Edge cases and error handling tests

## Test Requirements

All tests are configured to run with:
- pytest >= 8.0.0
- pytest-asyncio >= 0.23.0 (for async test support)
- pytest-mock >= 3.12.0 (for mocking)

Tests use `pytest.mark.asyncio` for async functions and are configured with `asyncio_mode = "auto"` in pyproject.toml.

## Coverage Goals

Target: >80% code coverage for meta_tools.py module.
