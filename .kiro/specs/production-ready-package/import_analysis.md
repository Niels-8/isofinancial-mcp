# Import Analysis for Datasources Refactoring

## Files to be Removed
1. `iso_financial_mcp/datasources/earnings_sources.py`
2. `iso_financial_mcp/datasources/trends_sources.py`

## Current Import Usage

### earnings_sources.py
**Imported by:**
- `iso_financial_mcp/datasources/earnings_source_manager.py`
  - Imports: `NasdaqEarnings`, `AlphaVantageEarnings`, `merge_earnings_data`, `estimate_next_earnings`
  - Line 10-14

**Functions/Classes in earnings_sources.py:**
- `merge_earnings_data()` - Merges and deduplicates earnings data from multiple sources
- `_normalize_date()` - Normalizes date strings to YYYY-MM-DD format
- `_merge_records()` - Merges two earnings records
- `estimate_next_earnings()` - Estimates next earnings date based on patterns
- `NasdaqEarnings` class - Nasdaq earnings data source
- `AlphaVantageEarnings` class - Alpha Vantage earnings data source

### trends_sources.py
**Imported by:**
- `iso_financial_mcp/datasources/trends_source_manager.py`
  - Imports: `PyTrendsDirect`, `PyTrendsWithProxy`, `SerpAPIFallback`
  - Line 14
- `tests/test_trends_source_manager.py`
  - Imports: `PyTrendsDirect`, `PyTrendsWithProxy`, `SerpAPIFallback`
  - Line 13-17

**Functions/Classes in trends_sources.py:**
- `PyTrendsDirect` class - Direct PyTrends implementation (primary source)
- `PyTrendsWithProxy` class - PyTrends with proxy support (secondary source)
- `SerpAPIFallback` class - SerpAPI as final fallback for Google Trends data

## Files NOT Importing These Modules
- `iso_financial_mcp/server.py` - Does NOT import earnings_sources or trends_sources
- `iso_financial_mcp/meta_tools.py` - Does NOT import earnings_sources or trends_sources
- `iso_financial_mcp/datasources/__init__.py` - Does NOT export earnings_sources or trends_sources
- `iso_financial_mcp/reliability/data_manager.py` - Does NOT import earnings_sources or trends_sources

## Consolidation Strategy

### For earnings_sources.py → earnings_source_manager.py
**Status:** ✅ ALREADY CONSOLIDATED
- All classes and functions from `earnings_sources.py` are already imported and used by `earnings_source_manager.py`
- The manager file acts as the public interface
- **Action Required:** 
  1. Move all code from `earnings_sources.py` into `earnings_source_manager.py`
  2. Remove the import statement from `earnings_source_manager.py`
  3. Delete `earnings_sources.py`

### For trends_sources.py → trends_source_manager.py
**Status:** ✅ ALREADY CONSOLIDATED
- All classes from `trends_sources.py` are already imported and used by `trends_source_manager.py`
- The manager file acts as the public interface
- **Action Required:**
  1. Move all code from `trends_sources.py` into `trends_source_manager.py`
  2. Remove the import statement from `trends_source_manager.py`
  3. Update test file `tests/test_trends_source_manager.py` to import from manager instead
  4. Delete `trends_sources.py`

## Files to Update

### 1. iso_financial_mcp/datasources/earnings_source_manager.py
- Remove import: `from .earnings_sources import ...`
- Add all code from `earnings_sources.py` directly into this file

### 2. iso_financial_mcp/datasources/trends_source_manager.py
- Remove import: `from .trends_sources import ...`
- Add all code from `trends_sources.py` directly into this file

### 3. tests/test_trends_source_manager.py
- Change import from:
  ```python
  from iso_financial_mcp.datasources.trends_sources import (
      PyTrendsDirect,
      PyTrendsWithProxy,
      SerpAPIFallback
  )
  ```
- To:
  ```python
  from iso_financial_mcp.datasources.trends_source_manager import (
      PyTrendsDirect,
      PyTrendsWithProxy,
      SerpAPIFallback
  )
  ```

## Validation Checklist
- [ ] All code from earnings_sources.py moved to earnings_source_manager.py
- [ ] All code from trends_sources.py moved to trends_source_manager.py
- [ ] Import statements removed from manager files
- [ ] Test file imports updated
- [ ] pytest runs successfully
- [ ] mypy type checking passes
- [ ] Server starts without errors
- [ ] earnings_sources.py deleted
- [ ] trends_sources.py deleted

## Notes
- No other files import these modules, so the consolidation is straightforward
- The manager files already act as the public interface
- This is a simple code relocation, not a refactoring
- All function signatures and behavior remain unchanged
