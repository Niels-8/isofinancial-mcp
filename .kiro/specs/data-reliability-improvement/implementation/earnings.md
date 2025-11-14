# Earnings Calendar Multi-Source Implementation

## Overview

This document describes the implementation of the earnings calendar improvements with multi-source fusion, automatic fallback, and intelligent estimation.

## Architecture

### Components

1. **earnings_sources.py**: Individual data source implementations
   - `NasdaqEarnings`: Nasdaq API earnings source
   - `AlphaVantageEarnings`: Alpha Vantage API earnings source
   - `merge_earnings_data()`: Data fusion and deduplication logic
   - `estimate_next_earnings()`: Earnings date estimation

2. **earnings_source_manager.py**: Orchestration layer
   - `EarningsSourceManager`: Manages multiple sources with fallback
   - Parallel fetching from all sources
   - Data fusion and validation
   - Cache integration

## Features

### Multi-Source Fallback

The system fetches earnings data from multiple sources in parallel:

1. **Nasdaq API** (Priority 1)
   - Comprehensive earnings calendar
   - Includes EPS estimates and actuals
   - Good coverage for US stocks

2. **Alpha Vantage** (Priority 2)
   - Quarterly earnings data
   - Requires API key (optional)
   - Good for historical data

### Data Fusion

The `merge_earnings_data()` function:
- Deduplicates earnings by date
- Normalizes different date formats
- Prioritizes records with EPS estimates
- Merges fields from multiple sources
- Tracks which sources contributed data

### Earnings Estimation

When no data is available, the system estimates next earnings date:

1. **Historical Pattern Analysis**
   - Calculates average interval between past earnings
   - Projects next date based on pattern
   - Validates reasonable quarterly intervals (60-120 days)

2. **Standard Quarterly Pattern**
   - Q1 (Jan-Mar): ~May 15 (45 days after Mar 31)
   - Q2 (Apr-Jun): ~Aug 15 (45 days after Jun 30)
   - Q3 (Jul-Sep): ~Nov 15 (45 days after Sep 30)
   - Q4 (Oct-Dec): ~Feb 15 (45 days after Dec 31)

### Future Date Validation

The system ensures at least one future earnings date exists:
- Checks all earnings dates against current date
- Adds estimated date if no future dates found
- Configurable via `require_future_date` parameter

## Usage

### Basic Usage

```python
from iso_financial_mcp.datasources.earnings_source_manager import EarningsSourceManager

# Initialize manager
manager = EarningsSourceManager()

# Fetch earnings with all features
result = await manager.fetch_earnings(
    ticker="AAPL",
    use_estimation=True,
    require_future_date=True
)

# Access data
earnings_data = result.data
source_used = result.source_used  # e.g., "nasdaq+alpha_vantage"
is_cached = result.is_cached
errors = result.errors
```

### With Alpha Vantage

```python
import os

# Initialize with Alpha Vantage API key
manager = EarningsSourceManager(
    alpha_vantage_key=os.getenv('ALPHA_VANTAGE_KEY')
)

result = await manager.fetch_earnings("AAPL")
```

### Custom Data Manager

```python
from iso_financial_mcp.reliability.data_manager import DataManager
from iso_financial_mcp.reliability.cache_layer import CacheLayer
from iso_financial_mcp.reliability.health_monitor import HealthMonitor

# Create custom components
cache = CacheLayer()
health = HealthMonitor()
data_manager = DataManager(cache_layer=cache, health_monitor=health)

# Initialize manager with custom data manager
manager = EarningsSourceManager(data_manager=data_manager)
```

## Data Format

### Earnings Record Structure

```python
{
    "date": "2024-05-15",              # Earnings date (YYYY-MM-DD)
    "period": "Q1 2024",               # Fiscal period
    "eps_estimate": 1.50,              # EPS estimate (optional)
    "eps_actual": 1.60,                # Actual EPS (optional)
    "eps_surprise": 0.10,              # Surprise amount (optional)
    "surprise_percentage": 6.67,       # Surprise % (optional)
    "timing": "AMC",                   # BMO/AMC/N/A
    "revenue_estimate": 90000000000,   # Revenue estimate (optional)
    "revenue_actual": 95000000000,     # Actual revenue (optional)
    "source": "nasdaq",                # Data source
    "sources": ["nasdaq", "alpha_vantage"],  # Multiple sources (if merged)
    "estimated": True                  # True if estimated (optional)
}
```

### DataResult Structure

```python
{
    "data": [...],                     # List of earnings records
    "source_used": "nasdaq+alpha_vantage",  # Sources that provided data
    "is_cached": False,                # True if from cache
    "cache_age_seconds": None,         # Cache age if cached
    "is_stale": False,                 # True if stale cache
    "attempted_sources": ["nasdaq", "alpha_vantage"],  # All attempted sources
    "errors": [...],                   # List of ErrorInfo objects
    "timestamp": datetime.now(),       # Fetch timestamp
    "partial_data": False              # True if some sources failed
}
```

## Error Handling

### Improved Nasdaq Error Handling

The Nasdaq source now handles:
- Non-dict responses
- Missing 'data' or 'rows' keys
- None values for rows
- Non-iterable rows
- Non-dict row items

All errors are logged with context and don't crash the system.

### Alpha Vantage Error Handling

Handles:
- Missing API key (raises ValueError)
- Rate limit errors (from API response)
- Network errors (aiohttp.ClientError)
- Invalid ticker symbols
- Malformed responses

### Graceful Degradation

- If one source fails, others are still tried
- Partial data is returned if any source succeeds
- Estimation fallback if all sources fail
- Stale cache as last resort

## Health Monitoring

### Get Health Status

```python
# Get health status for all earnings sources
status = manager.get_health_status()

# Example output:
{
    "nasdaq": {
        "success_rate": 0.95,
        "avg_latency_ms": 450,
        "total_requests": 100,
        "status": "healthy",
        "last_success": "2024-11-13T10:30:00"
    },
    "alpha_vantage": {
        "success_rate": 0.88,
        "avg_latency_ms": 650,
        "total_requests": 50,
        "status": "healthy",
        "last_success": "2024-11-13T10:25:00"
    }
}
```

## Caching

### Cache Strategy

- **Memory cache**: 1 hour TTL
- **Disk cache**: 24 hours TTL
- **Cache key**: `earnings_{ticker}`
- **Stale fallback**: Enabled

### Cache Behavior

1. Check cache first (fresh data only)
2. If cache miss, fetch from sources
3. Cache successful results
4. On total failure, return stale cache if available

## Configuration

### Environment Variables

```bash
# Optional: Alpha Vantage API key
export ALPHA_VANTAGE_KEY="your_api_key_here"
```

### Source Priority

Sources are tried in parallel, but results are prioritized:
1. Records with EPS estimates preferred
2. Non-None values preferred when merging
3. Multiple sources tracked in merged records

## Testing

### Unit Tests

Test individual components:

```python
# Test data merging
earnings1 = [{"date": "2024-05-15", "eps_estimate": 1.5, "source": "nasdaq"}]
earnings2 = [{"date": "2024-05-15", "eps_actual": 1.6, "source": "alpha_vantage"}]
merged = merge_earnings_data([earnings1, earnings2])
assert len(merged) == 1
assert merged[0]["eps_estimate"] == 1.5
assert merged[0]["eps_actual"] == 1.6

# Test estimation
estimated = estimate_next_earnings("TEST")
assert estimated["estimated"] == True
assert estimated["date"] > datetime.now().strftime("%Y-%m-%d")
```

### Integration Tests

Test complete flow:

```python
manager = EarningsSourceManager()
result = await manager.fetch_earnings("AAPL")
assert result.data is not None
assert len(result.data) > 0
assert any(e["date"] > datetime.now().strftime("%Y-%m-%d") for e in result.data)
```

## Performance

### Parallel Fetching

All sources are fetched in parallel using `asyncio.gather()`:
- Reduces total latency
- Maximizes data coverage
- Continues even if one source fails

### Typical Latencies

- Nasdaq API: 300-500ms
- Alpha Vantage: 500-800ms
- Total (parallel): ~500-800ms (max of both)
- Cache hit: <10ms

## Troubleshooting

### No Data Returned

1. Check if ticker is valid
2. Verify Alpha Vantage API key if using
3. Check health status: `manager.get_health_status()`
4. Review error messages in `result.errors`

### Estimation Always Used

1. Check if sources are returning data
2. Verify network connectivity
3. Check API rate limits
4. Review source-specific logs

### Future Date Validation Fails

1. Check if earnings data is recent
2. Verify date parsing is working
3. Enable estimation: `use_estimation=True`
4. Check if `require_future_date=True` is needed

## Requirements Satisfied

This implementation satisfies all requirements from the spec:

- ✅ **Req 3.1**: Multiple earnings sources (Nasdaq, Alpha Vantage)
- ✅ **Req 3.2**: Automatic fallback between sources
- ✅ **Req 3.3**: Data fusion and deduplication
- ✅ **Req 3.4**: Earnings date estimation fallback
- ✅ **Req 3.5**: Future date validation

## Future Enhancements

Potential improvements:
1. Add more sources (Financial Modeling Prep, Seeking Alpha)
2. Machine learning for better estimation
3. Earnings surprise prediction
4. Historical pattern analysis improvements
5. Real-time earnings alerts
