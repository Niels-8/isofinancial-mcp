# Google Trends Data Sources

## Overview

The trends module uses a multi-source fallback strategy to provide reliable search trend data despite Google's aggressive bot detection (429 errors).

## Source Priority

Sources are tried in this order:

### 1. SerpAPI (Primary - if configured)
- **Status**: Optional, requires API key
- **Reliability**: ⭐⭐⭐⭐⭐ Excellent
- **Data Quality**: ⭐⭐⭐⭐⭐ Full Google Trends data
- **Cost**: Paid service (~$50/month for 5000 searches)
- **Configuration**: Set `SERPAPI_KEY` environment variable

**Pros:**
- Official Google Trends API access
- No rate limiting issues
- Full time series data
- Related queries included

**Cons:**
- Requires paid API key
- Additional dependency

### 2. DuckDuckGo Search (Secondary - always available)
- **Status**: Always available, no configuration needed
- **Reliability**: ⭐⭐⭐⭐ Good
- **Data Quality**: ⭐⭐⭐ Estimated (not actual search volume)
- **Cost**: Free
- **Configuration**: None required

**Pros:**
- Free and bot-friendly
- No rate limiting
- No API key needed
- Fast response times

**Cons:**
- Provides estimated interest, not actual search volume
- Single data point (current), no time series
- Based on search result richness, not actual trends

**How it works:**
- Queries DuckDuckGo instant answer API
- Estimates interest level based on:
  - Presence of abstract (30 points)
  - Number of related topics (up to 40 points)
  - Number of results (up to 30 points)
- Returns simplified trend data (0-100 scale)

### 3. PyTrends Direct (Tertiary - often fails)
- **Status**: Always attempted as last resort
- **Reliability**: ⭐ Poor (frequent 429 errors)
- **Data Quality**: ⭐⭐⭐⭐⭐ Full Google Trends data (when it works)
- **Cost**: Free
- **Configuration**: None required

**Pros:**
- Free
- Full Google Trends data when it works
- No API key needed

**Cons:**
- Frequent 429 (Too Many Requests) errors
- Google actively blocks bots
- Unreliable for production use
- Only 1 retry attempt (more retries don't help)

### 4. PyTrends with Proxy (Optional)
- **Status**: Optional, requires proxy configuration
- **Reliability**: ⭐⭐ Fair (depends on proxy quality)
- **Data Quality**: ⭐⭐⭐⭐⭐ Full Google Trends data
- **Cost**: Proxy service cost
- **Configuration**: Set `TRENDS_PROXY` environment variable

**Pros:**
- Can bypass some rate limiting
- Full Google Trends data

**Cons:**
- Requires proxy service
- Still subject to 429 errors
- Additional complexity

## Configuration

### Using SerpAPI (Recommended for Production)

```bash
# Set environment variable
export SERPAPI_KEY="your_api_key_here"

# Or in .env file
SERPAPI_KEY=your_api_key_here
```

Get an API key at: https://serpapi.com/

### Using Proxy for PyTrends (Optional)

```bash
# Set environment variable
export TRENDS_PROXY="http://proxy.example.com:8080"

# Or in .env file
TRENDS_PROXY=http://proxy.example.com:8080
```

### Default Configuration (No Setup Required)

If no configuration is provided:
1. DuckDuckGo will be used as primary source (free, reliable)
2. PyTrends will be attempted as fallback (often fails with 429)

## Usage Examples

### Basic Usage

```python
from iso_financial_mcp.datasources.trends_source_manager import TrendsSourceManager

manager = TrendsSourceManager()

# Fetch trends data (automatically uses best available source)
result = await manager.fetch_trends("AAPL", window_days=30)

print(f"Source used: {result.source_used}")
print(f"Latest value: {result.data['latest']}")
print(f"Attempted sources: {result.attempted_sources}")
```

### Checking Source Priority

```python
manager = TrendsSourceManager()

# See which sources are configured
print(f"Available sources: {[name for name, _ in manager.sources]}")

# Example output:
# - With SerpAPI: ['serpapi', 'duckduckgo', 'pytrends_direct']
# - Without SerpAPI: ['duckduckgo', 'pytrends_direct']
```

### Handling Results

```python
result = await manager.fetch_trends("TSLA", window_days=30)

if result.data:
    # Check data source
    source = result.data.get('source', result.source_used)
    
    if source == 'duckduckgo':
        print("Note: Estimated trend data from DuckDuckGo")
        print(f"Estimated interest: {result.data['latest']}")
    elif source == 'serpapi':
        print("Full Google Trends data from SerpAPI")
        print(f"Time series points: {result.data['total_points']}")
    elif source.startswith('pytrends'):
        print("Full Google Trends data from PyTrends")
        print(f"Time series points: {result.data['total_points']}")
```

## Error Handling

The manager implements graceful degradation:

1. **Primary source fails**: Automatically tries next source
2. **All sources fail**: Returns stale cache if available
3. **No cache available**: Returns empty result with error details

```python
result = await manager.fetch_trends("AAPL")

if result.errors:
    print("Some sources failed:")
    for error in result.errors:
        print(f"  - {error.source}: {error.error_type}")

if result.is_stale:
    print(f"Warning: Using stale cache (age: {result.cache_age_seconds}s)")

if not result.data:
    print("No data available from any source")
```

## Performance Characteristics

| Source | Typical Latency | Success Rate | Data Quality |
|--------|----------------|--------------|--------------|
| SerpAPI | 500-1000ms | 99%+ | Excellent |
| DuckDuckGo | 200-500ms | 95%+ | Good (estimated) |
| PyTrends Direct | 1000-3000ms | 10-30% | Excellent (when works) |
| PyTrends Proxy | 1000-4000ms | 30-60% | Excellent (when works) |

## Caching

All trends data is cached for 24 hours to:
- Reduce API calls
- Improve response times
- Provide fallback when all sources fail

Cache key format: `trends_{term}_{window_days}`

## Recommendations

### For Development
- Use default configuration (DuckDuckGo + PyTrends)
- Accept estimated data from DuckDuckGo
- Don't rely on PyTrends working consistently

### For Production
- **Recommended**: Configure SerpAPI for reliable, high-quality data
- **Alternative**: Use DuckDuckGo only (disable PyTrends to avoid delays)
- Monitor source usage via health metrics

### For High-Volume Applications
- Use SerpAPI (paid but reliable)
- Implement aggressive caching (24h+ TTL)
- Consider pre-fetching popular tickers

## Troubleshooting

### PyTrends Always Fails with 429
**Expected behavior**. Google actively blocks bots. Solutions:
1. Configure SerpAPI (recommended)
2. Rely on DuckDuckGo (free alternative)
3. Configure proxy (may help but not guaranteed)

### DuckDuckGo Returns Low Values
DuckDuckGo provides estimated interest, not actual search volume. Values are relative indicators, not absolute metrics.

### Want Actual Time Series Data
Configure SerpAPI. DuckDuckGo only provides current snapshot, not historical time series.

## Future Improvements

Potential enhancements:
- Add more free search APIs (Bing, Yahoo)
- Implement rotating proxy pool for PyTrends
- Add web scraping fallback (last resort)
- Support custom source priority configuration
