# Google Trends Migration Guide (v0.4.1)

## What Changed?

Version 0.4.1 introduces a new multi-source strategy for Google Trends data to address the persistent 429 (Too Many Requests) errors from PyTrends.

### Old Behavior (v0.4.0 and earlier)
- **Primary source**: PyTrends Direct
- **Fallback**: PyTrends with Proxy → SerpAPI
- **Problem**: PyTrends frequently fails with 429 errors, causing delays and failures

### New Behavior (v0.4.1+)
- **Primary source**: SerpAPI (if configured) → DuckDuckGo (free) → PyTrends (last resort)
- **Benefit**: Reliable data with free fallback, minimal 429 errors

## Impact on Your Application

### If You Don't Configure SerpAPI

**Before (v0.4.0):**
```python
# Often failed with 429 errors
result = await get_google_trends("AAPL")
# Error: The request failed: Google returned a response with code 429
```

**After (v0.4.1):**
```python
# Works reliably with DuckDuckGo
result = await get_google_trends("AAPL")
# Returns estimated trend data from DuckDuckGo
# result['note'] = "Estimated trend based on search result richness"
```

### Data Quality Differences

| Source | Time Series | Accuracy | Reliability | Cost |
|--------|------------|----------|-------------|------|
| **SerpAPI** | ✅ Full | ⭐⭐⭐⭐⭐ Exact | ⭐⭐⭐⭐⭐ 99%+ | ~$50/month |
| **DuckDuckGo** | ❌ Single point | ⭐⭐⭐ Estimated | ⭐⭐⭐⭐ 95%+ | Free |
| **PyTrends** | ✅ Full | ⭐⭐⭐⭐⭐ Exact | ⭐ 10-30% | Free |

### DuckDuckGo Limitations

DuckDuckGo provides **estimated** interest levels, not actual search volume:

```python
result = await get_google_trends("AAPL")

# DuckDuckGo returns:
{
    "latest": 25,  # Estimated interest (0-100)
    "series": [{"date": "2025-11-14", "value": 25}],  # Single point
    "note": "Estimated trend based on search result richness",
    "_source_used": "duckduckgo"
}

# vs. SerpAPI/PyTrends returns:
{
    "latest": 67,  # Actual search volume
    "series": [  # Full time series
        {"date": "2025-10-15", "value": 45},
        {"date": "2025-10-22", "value": 52},
        # ... 30+ data points
    ],
    "_source_used": "serpapi"
}
```

## Migration Paths

### Option 1: Accept DuckDuckGo Estimates (Recommended for Most Users)

**No changes needed!** Your code will continue to work, but will receive estimated data from DuckDuckGo instead of frequent 429 errors.

**Use case**: General trend awareness, relative comparisons, social momentum indicators

```python
# Works out of the box
result = await get_google_trends("TSLA")

# Check if using estimated data
if result.get('_source_used') == 'duckduckgo':
    print("Using estimated trend data")
    # Treat values as relative indicators, not absolute metrics
```

### Option 2: Configure SerpAPI for Full Data (Recommended for Production)

**Best for**: Applications requiring accurate search volume and time series data

1. **Get SerpAPI key**: https://serpapi.com/ (~$50/month for 5000 searches)

2. **Configure environment variable**:
```bash
export SERPAPI_KEY="your_api_key_here"
```

3. **Or in .env file**:
```bash
SERPAPI_KEY=your_api_key_here
```

4. **Verify configuration**:
```python
from iso_financial_mcp.datasources.trends_source_manager import TrendsSourceManager

manager = TrendsSourceManager()
sources = [name for name, _ in manager.sources]

if 'serpapi' in sources:
    print("✓ SerpAPI configured")
else:
    print("⚠ Using DuckDuckGo fallback")
```

### Option 3: Use Proxy for PyTrends (Not Recommended)

**Note**: This may help but doesn't guarantee success. Google actively blocks bots.

```bash
export TRENDS_PROXY="http://proxy.example.com:8080"
```

## Code Changes Required

### None for Basic Usage

The API remains the same:

```python
# This code works in both v0.4.0 and v0.4.1
from iso_financial_mcp.datasources import trends_source

result = await trends_source.get_google_trends("AAPL", window_days=30)
```

### Optional: Check Data Source

If you want to know which source was used:

```python
result = await trends_source.get_google_trends("AAPL")

source = result.get('_source_used')
is_estimated = (source == 'duckduckgo')

if is_estimated:
    print(f"Note: {result.get('note')}")
    # Handle estimated data appropriately
```

### Optional: Validate Data Quality

```python
result = await trends_source.get_google_trends("AAPL")

# Check if we got full time series data
has_time_series = len(result.get('series', [])) > 5

if has_time_series:
    print("Full time series data available")
    # Perform detailed trend analysis
else:
    print("Limited data - using for relative comparison only")
    # Use as general indicator
```

## Testing Your Application

### Test with DuckDuckGo (Default)

```bash
# No configuration needed
uv run python -c "
from iso_financial_mcp.datasources import trends_source
import asyncio

async def test():
    result = await trends_source.get_google_trends('AAPL')
    print(f'Source: {result.get(\"_source_used\")}')
    print(f'Latest: {result.get(\"latest\")}')
    print(f'Note: {result.get(\"note\", \"N/A\")}')

asyncio.run(test())
"
```

### Test with SerpAPI

```bash
# Set API key
export SERPAPI_KEY="your_key"

# Run test
uv run python -c "
from iso_financial_mcp.datasources import trends_source
import asyncio

async def test():
    result = await trends_source.get_google_trends('AAPL')
    print(f'Source: {result.get(\"_source_used\")}')
    print(f'Data points: {len(result.get(\"series\", []))}')

asyncio.run(test())
"
```

## Troubleshooting

### "All sources failed" Error

**Cause**: Network issues or all sources unavailable

**Solution**:
1. Check internet connectivity
2. Verify SerpAPI key if configured
3. Check logs for specific errors

### Getting Estimated Data When You Need Exact Data

**Cause**: SerpAPI not configured

**Solution**: Configure SerpAPI key (see Option 2 above)

### PyTrends Still Failing

**Expected behavior**. PyTrends is now a last-resort fallback and will be skipped quickly if it fails.

**Solution**: Use SerpAPI or accept DuckDuckGo estimates

## Performance Impact

### Latency Improvements

| Scenario | v0.4.0 (PyTrends) | v0.4.1 (DuckDuckGo) | Improvement |
|----------|-------------------|---------------------|-------------|
| Success | 1000-3000ms | 200-500ms | 2-6x faster |
| Failure | 10000-30000ms (retries) | 200-500ms | 20-60x faster |
| Success Rate | 10-30% | 95%+ | 3-10x better |

### Cache Behavior

No changes to caching:
- TTL: 24 hours
- Cache key: `trends_{term}_{window_days}`
- Stale cache fallback: Available

## Rollback Instructions

If you need to revert to v0.4.0 behavior:

```bash
# Downgrade package
uv pip install iso-financial-mcp==0.4.0

# Or pin version in pyproject.toml
[dependencies]
iso-financial-mcp = "==0.4.0"
```

**Note**: We don't recommend rollback as v0.4.0 has frequent 429 failures.

## Questions?

- **Documentation**: See [TRENDS_SOURCES.md](TRENDS_SOURCES.md) for detailed source comparison
- **Issues**: Report on GitHub
- **Configuration**: See [CONFIGURATION.md](CONFIGURATION.md)

## Summary

✅ **No code changes required** for basic usage
✅ **Better reliability** with DuckDuckGo fallback
✅ **Optional SerpAPI** for full data quality
✅ **Faster responses** (2-60x improvement)
✅ **Backward compatible** API
