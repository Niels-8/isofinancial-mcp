# Meta Tools Integration with Reliability Infrastructure

## Overview

This document describes the integration of the reliability infrastructure (DataManager, source managers, error handling) with the existing `meta_tools.py` module.

## Changes Made

### 1. Module Imports

Added imports for reliability components:
- `DataManager` from `reliability.data_manager`
- `DataResult` model from `reliability.models`
- Source managers: `SECSourceManager`, `TrendsSourceManager`, `EarningsSourceManager`

### 2. Global Manager Instances

Created singleton instances for reuse across multiple calls:
- `_data_manager`: Global DataManager instance
- `_sec_manager`: Global SECSourceManager instance
- `_trends_manager`: Global TrendsSourceManager instance
- `_earnings_manager`: Global EarningsSourceManager instance

Helper functions to get or create these instances:
- `_get_data_manager()`
- `_get_sec_manager()`
- `_get_trends_manager()`
- `_get_earnings_manager()`

### 3. Updated `get_financial_snapshot()`

**Key Changes:**
- Now uses source managers for SEC, Trends, and Earnings data
- Handles `DataResult` objects returned by source managers
- Extracts metadata from `DataResult` (source used, cache status, errors)
- Stores metadata in new `snapshot["metadata"]` field
- Maintains backward compatibility with direct source calls (yfinance, news, FINRA)

**New Snapshot Structure:**
```python
{
    "ticker": "AAPL",
    "timestamp": "2025-11-13T17:57:17.834740",
    "data": {
        "info": {...},
        "prices": {...},
        "news": [...],
        "sec_filings": {...},
        "earnings": {...},
        "short_volume": {...},
        "google_trends": {...}
    },
    "errors": [...],
    "metadata": {  # NEW
        "sec_filings": {
            "source_used": "sec_edgar_api",
            "is_cached": false,
            "cache_age_seconds": null,
            "is_stale": false,
            "attempted_sources": ["sec_edgar_api"],
            "successful_sources": ["sec_edgar_api"],
            "failed_sources": [],
            "partial_data": false,
            "last_successful_update": "2025-11-13T17:57:17.834740"
        },
        "earnings": {...},
        "google_trends": {...}
    }
}
```

### 4. Updated `format_snapshot_for_llm()`

**New Features:**
- Displays data source information at the top
- Shows cache status (fresh, cached, stale) with visual indicators
- Indicates when fallback was used
- Shows detailed error information with suggested actions

**Example Output:**
```
=== FINANCIAL SNAPSHOT: AAPL ===
Timestamp: 2025-11-13T17:57:17.834740

--- DATA SOURCES ---
sec_filings: sec_edgar_api [✓ FRESH]
earnings: estimated [✓ FRESH]
  └─ Fallback used (failed: earnings_alpha_vantage)
google_trends: none [✓ FRESH]
  └─ Fallback used (failed: pytrends_direct, pytrends_proxy, serpapi_fallback)

--- COMPANY INFORMATION ---
...

--- DETAILED ERROR INFORMATION ---
1. earnings - earnings_alpha_vantage
   Type: unauthorized
   Message: Authentication failed: Alpha Vantage API key not configured
   💡 Suggested Action: Check API key configuration in environment variables.
```

## Benefits

### 1. Automatic Fallback
- SEC filings automatically extend lookback from 30 to 90 days if no results
- Multiple sources tried in priority order
- Stale cache used as last resort

### 2. Improved Error Handling
- Detailed error classification (rate_limit, timeout, not_found, etc.)
- Actionable error messages with suggested fixes
- Partial data support (some sources succeed, others fail)

### 3. Caching & Performance
- Two-level caching (memory + disk)
- Cache hit information displayed to users
- Stale data fallback prevents complete failures

### 4. Health Monitoring
- Success/failure rates tracked per source
- Latency metrics collected
- Unhealthy sources automatically deprioritized

### 5. Backward Compatibility
- Existing API unchanged
- Direct sources (yfinance, news, FINRA) still work
- Metadata is optional - old code ignores it

## Testing

Tested with live data for AAPL:
- ✅ SEC filings: Extended lookback worked, found 2 filings
- ✅ Earnings: Estimation fallback worked when sources failed
- ✅ Trends: Rate limit detected, retry with backoff attempted
- ✅ Metadata: Correctly captured source, cache status, errors
- ✅ Formatting: New sections displayed properly

## Future Enhancements

1. **Add more sources to managers**
   - yfinance could use DataManager for caching
   - news could have alternative RSS feeds
   - FINRA could have backup sources

2. **Expose health status**
   - Add tool to query source health
   - Display health in formatted output
   - Alert on degraded sources

3. **Configuration**
   - Allow users to configure source priorities
   - Customize cache TTLs per data type
   - Enable/disable specific sources

4. **Metrics Dashboard**
   - Track cache hit rates
   - Monitor source reliability over time
   - Identify patterns in failures

## Migration Notes

For users upgrading from previous versions:
- No code changes required
- New metadata field is optional
- Error messages are more detailed but backward compatible
- Performance may improve due to caching
- Some sources may take longer on first call (cache warming)

## Related Files

- `iso_financial_mcp/meta_tools.py` - Main integration point
- `iso_financial_mcp/reliability/data_manager.py` - Orchestration layer
- `iso_financial_mcp/datasources/sec_source_manager.py` - SEC multi-source
- `iso_financial_mcp/datasources/trends_source_manager.py` - Trends with retry
- `iso_financial_mcp/datasources/earnings_source_manager.py` - Earnings fusion
