# IsoFinancial-MCP Configuration Guide

## Overview

IsoFinancial-MCP is designed to work out-of-the-box with **zero configuration required**. All core data sources use free, public APIs that don't require API keys. However, you can optionally configure additional data sources for enhanced functionality.

## Quick Start

No configuration needed! Just install and run:

```bash
# Install
uv pip install iso-financial-mcp

# Run
uv run python -m iso_financial_mcp
```

## Configuration Methods

IsoFinancial-MCP supports three configuration methods with the following priority order:

**Priority Order (highest to lowest):**
1. **MCP Tools** (runtime configuration via MCP protocol)
2. **Environment Variables** (shell environment)
3. **YAML Configuration File** (persistent configuration)
4. **Default Values** (built-in defaults)

### Method 1: MCP Tools (Recommended)

Configure the server at runtime using MCP tools. This is the most convenient method for interactive use.

**Available Tools:**
- `configure_api_key`: Set API keys for optional providers
- `get_configuration`: View current configuration (keys masked)
- `list_data_sources`: See all available data sources and their status

**Example Usage:**

```python
# Configure Alpha Vantage API key
await configure_api_key("alpha_vantage", "YOUR_API_KEY_HERE")

# View current configuration
await get_configuration()

# List all data sources
await list_data_sources()
```

**Benefits:**
- No file editing required
- Immediate effect (no restart needed)
- Configuration persists to YAML file automatically
- Keys are validated on configuration

### Method 2: Environment Variables

Set configuration via environment variables in your shell or `.env` file.

**Naming Convention:**
- Convert config keys to UPPERCASE
- Replace dots (`.`) with underscores (`_`)
- Example: `alpha_vantage.api_key` → `ALPHA_VANTAGE_API_KEY`

**Example:**

```bash
# In your shell
export ALPHA_VANTAGE_API_KEY="your_key_here"
export SERPAPI_API_KEY="your_key_here"

# Or in .env file
ALPHA_VANTAGE_API_KEY=your_key_here
SERPAPI_API_KEY=your_key_here
CACHE_MEMORY_TTL_SECONDS=300
CACHE_DISK_TTL_SECONDS=3600
```

**Benefits:**
- Standard Unix/Linux pattern
- Works with Docker and container orchestration
- Easy to manage in CI/CD pipelines
- No files to commit to version control

### Method 3: YAML Configuration File

Create a persistent configuration file for your settings.

**Location:** `~/.iso_financial_mcp/config/datasources.yaml`

**Example Configuration:**

```yaml
# API Keys (optional)
alpha_vantage:
  api_key: "YOUR_ALPHA_VANTAGE_KEY"
  
serpapi:
  api_key: "YOUR_SERPAPI_KEY"

# Cache Configuration
cache:
  memory:
    ttl_seconds: 300  # 5 minutes
    max_size_mb: 100
  disk:
    ttl_seconds: 3600  # 1 hour
    max_size_mb: 500
    path: "~/.iso_financial_mcp/cache"

# Rate Limiting
rate_limits:
  yahoo_finance:
    calls_per_minute: 60
  sec_edgar:
    calls_per_minute: 10
  google_trends:
    calls_per_minute: 20

# Health Monitoring
health:
  check_interval_seconds: 60
  failure_threshold: 3
  recovery_threshold: 2
```

**Benefits:**
- Persistent configuration across sessions
- Easy to version control (without sensitive keys)
- Supports complex nested configuration
- Human-readable format

## Optional API Keys

All API keys are **optional**. The server works perfectly without them using free, public data sources.

### Alpha Vantage

**Purpose:** Enhanced earnings data and additional financial metrics

**Free Tier:** 25 requests/day, 5 requests/minute

**Get Your Key:** [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)

**Configuration:**

```bash
# Via MCP Tool
await configure_api_key("alpha_vantage", "YOUR_KEY")

# Via Environment Variable
export ALPHA_VANTAGE_API_KEY="YOUR_KEY"

# Via YAML
alpha_vantage:
  api_key: "YOUR_KEY"
```

**What You Get:**
- Additional earnings data source (fallback for primary sources)
- Enhanced financial metrics
- More reliable earnings calendar

### SerpAPI

**Purpose:** Google Trends fallback when primary source is rate-limited

**Free Tier:** 100 searches/month

**Get Your Key:** [https://serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)

**Configuration:**

```bash
# Via MCP Tool
await configure_api_key("serpapi", "YOUR_KEY")

# Via Environment Variable
export SERPAPI_API_KEY="YOUR_KEY"

# Via YAML
serpapi:
  api_key: "YOUR_KEY"
```

**What You Get:**
- Fallback for Google Trends when rate-limited
- More reliable trends data during high usage
- Extended rate limit capacity

## Configuration Options

### Cache Settings

Control how data is cached to improve performance and reduce API calls.

**Memory Cache:**
```yaml
cache:
  memory:
    ttl_seconds: 300      # Time to live (5 minutes)
    max_size_mb: 100      # Maximum memory usage
```

**Disk Cache:**
```yaml
cache:
  disk:
    ttl_seconds: 3600     # Time to live (1 hour)
    max_size_mb: 500      # Maximum disk usage
    path: "~/.iso_financial_mcp/cache"
```

**Per-Source TTL:**
```yaml
cache:
  ttl_by_source:
    market_data: 300      # 5 minutes
    options: 900          # 15 minutes
    news: 7200            # 2 hours
    sec_filings: 21600    # 6 hours
    finra: 86400          # 24 hours
    earnings: 86400       # 24 hours
    trends: 86400         # 24 hours
```

### Rate Limiting

Configure rate limits to respect API provider constraints.

```yaml
rate_limits:
  yahoo_finance:
    calls_per_minute: 60
    calls_per_day: null   # Unlimited
    
  sec_edgar:
    calls_per_minute: 10  # SEC limit: 10 req/sec
    calls_per_day: null
    
  google_trends:
    calls_per_minute: 20
    calls_per_day: 1000
    
  finra:
    calls_per_minute: 30
    calls_per_day: null
    
  rss_feeds:
    calls_per_minute: 30
    calls_per_day: null
```

### Health Monitoring

Configure health check behavior.

```yaml
health:
  check_interval_seconds: 60    # How often to check source health
  failure_threshold: 3          # Failures before marking unhealthy
  recovery_threshold: 2         # Successes before marking healthy
  timeout_seconds: 10           # Timeout for health checks
```

### Logging

Configure logging behavior.

```yaml
logging:
  level: "INFO"                 # DEBUG, INFO, WARNING, ERROR
  format: "json"                # json or text
  file: "~/.iso_financial_mcp/logs/server.log"
  max_size_mb: 100
  backup_count: 5
```

## Configuration Priority Example

Understanding how configuration priority works:

```yaml
# ~/.iso_financial_mcp/config/datasources.yaml
alpha_vantage:
  api_key: "YAML_KEY"
cache:
  memory:
    ttl_seconds: 300
```

```bash
# Environment variable
export ALPHA_VANTAGE_API_KEY="ENV_KEY"
```

```python
# MCP Tool
await configure_api_key("alpha_vantage", "MCP_KEY")
```

**Result:**
- `alpha_vantage.api_key` = `"MCP_KEY"` (MCP tools have highest priority)
- `cache.memory.ttl_seconds` = `300` (from YAML, no override)

## Viewing Current Configuration

Use the `get_configuration` MCP tool to view your current configuration:

```python
await get_configuration()
```

**Example Output:**

```
📋 Current Configuration:

🔑 API Keys:
  • alpha_vantage: ...XY12 ✓
  • serpapi: Not configured

💾 Cache:
  • Memory TTL: 300s
  • Disk TTL: 3600s
  • Max size: 500MB

⚡ Rate Limits:
  • Yahoo Finance: 60/min
  • SEC EDGAR: 10/min
  • Google Trends: 20/min

🏥 Health Monitoring:
  • Check interval: 60s
  • Failure threshold: 3
  • Recovery threshold: 2
```

## Listing Data Sources

Use the `list_data_sources` MCP tool to see all available sources:

```python
await list_data_sources()
```

**Example Output:**

```
📊 Available Data Sources:

✅ Yahoo Finance
   Market data, financials, options

✅ SEC EDGAR
   SEC filings (8-K, 10-Q, 10-K, etc.)

✅ FINRA
   Short volume data

✅ Google Trends
   Search volume trends

⚠️ Alpha Vantage (requires API key)
   Additional earnings data

⚠️ SerpAPI (requires API key)
   Google Trends fallback
```

## Troubleshooting

### Issue: "API key validation failed"

**Cause:** The API key you provided is invalid or expired.

**Solution:**
1. Verify your API key at the provider's website
2. Check for typos in the key
3. Ensure the key has the correct permissions
4. Try generating a new key

### Issue: "Rate limit exceeded"

**Cause:** You've exceeded the rate limit for a data source.

**Solution:**
1. Wait for the rate limit window to reset
2. Configure an API key for additional capacity (Alpha Vantage, SerpAPI)
3. Adjust rate limits in configuration if you have higher limits
4. Use caching to reduce API calls

### Issue: "Configuration not persisting"

**Cause:** File permissions or path issues.

**Solution:**
1. Check that `~/.iso_financial_mcp/config/` directory exists
2. Verify write permissions: `ls -la ~/.iso_financial_mcp/config/`
3. Create directory manually: `mkdir -p ~/.iso_financial_mcp/config/`
4. Check disk space: `df -h ~`

### Issue: "Environment variables not working"

**Cause:** Variables not exported or incorrect naming.

**Solution:**
1. Verify variable is exported: `echo $ALPHA_VANTAGE_API_KEY`
2. Check naming convention (UPPERCASE, underscores)
3. Restart the server after setting variables
4. Use `.env` file with `python-dotenv`

### Issue: "Cache not working"

**Cause:** Cache directory permissions or disk space.

**Solution:**
1. Check cache directory exists: `ls -la ~/.iso_financial_mcp/cache/`
2. Verify write permissions
3. Check disk space: `df -h ~`
4. Clear cache manually: `rm -rf ~/.iso_financial_mcp/cache/*`
5. Adjust cache size limits in configuration

### Issue: "Data seems stale"

**Cause:** Cache TTL too long for your use case.

**Solution:**
1. Reduce TTL for specific data sources
2. Clear cache: `rm -rf ~/.iso_financial_mcp/cache/*`
3. Adjust per-source TTL in configuration
4. Disable caching for real-time data needs

### Issue: "Server won't start"

**Cause:** Configuration file syntax error or missing dependencies.

**Solution:**
1. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('~/.iso_financial_mcp/config/datasources.yaml'))"`
2. Check for missing dependencies: `uv pip list`
3. Reinstall package: `uv pip install --force-reinstall iso-financial-mcp`
4. Check logs: `cat ~/.iso_financial_mcp/logs/server.log`

## Best Practices

### Security

1. **Never commit API keys to version control**
   - Use `.env` files and add to `.gitignore`
   - Use environment variables in production
   - Use secrets management in cloud deployments

2. **Rotate API keys regularly**
   - Generate new keys periodically
   - Revoke old keys after rotation
   - Monitor key usage for anomalies

3. **Use minimal permissions**
   - Request only necessary API permissions
   - Use read-only keys when possible
   - Separate keys for dev/staging/prod

### Performance

1. **Tune cache TTL for your use case**
   - Shorter TTL for real-time trading
   - Longer TTL for research and analysis
   - Balance freshness vs API usage

2. **Monitor rate limits**
   - Track API usage with health monitoring
   - Configure alerts for rate limit warnings
   - Use caching to stay under limits

3. **Use appropriate rate limits**
   - Don't exceed provider limits
   - Leave headroom for bursts
   - Adjust based on your API tier

### Reliability

1. **Configure multiple data sources**
   - Add Alpha Vantage for earnings fallback
   - Add SerpAPI for trends fallback
   - Benefit from automatic failover

2. **Monitor source health**
   - Use `get_health_status` tool regularly
   - Set up alerts for unhealthy sources
   - Review error logs periodically

3. **Test configuration changes**
   - Test in development first
   - Verify with `get_configuration` tool
   - Monitor logs after changes

## Configuration Examples

### Minimal Configuration (Default)

No configuration file needed! Just run the server.

### Development Configuration

```yaml
# ~/.iso_financial_mcp/config/datasources.yaml
cache:
  memory:
    ttl_seconds: 60      # Short TTL for fresh data
  disk:
    ttl_seconds: 300

logging:
  level: "DEBUG"         # Verbose logging
  format: "text"         # Human-readable
```

### Production Configuration

```yaml
# ~/.iso_financial_mcp/config/datasources.yaml
alpha_vantage:
  api_key: "${ALPHA_VANTAGE_API_KEY}"  # From environment

serpapi:
  api_key: "${SERPAPI_API_KEY}"

cache:
  memory:
    ttl_seconds: 300
    max_size_mb: 200
  disk:
    ttl_seconds: 3600
    max_size_mb: 1000

rate_limits:
  yahoo_finance:
    calls_per_minute: 60
  sec_edgar:
    calls_per_minute: 10

health:
  check_interval_seconds: 30
  failure_threshold: 5
  recovery_threshold: 3

logging:
  level: "INFO"
  format: "json"
  file: "/var/log/iso_financial_mcp/server.log"
```

### High-Performance Configuration

```yaml
# ~/.iso_financial_mcp/config/datasources.yaml
cache:
  memory:
    ttl_seconds: 600     # Longer TTL
    max_size_mb: 500     # More memory
  disk:
    ttl_seconds: 7200
    max_size_mb: 2000    # More disk

rate_limits:
  yahoo_finance:
    calls_per_minute: 120  # Higher limits
  google_trends:
    calls_per_minute: 40

logging:
  level: "WARNING"       # Less logging overhead
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system design
- Read [RELIABILITY.md](RELIABILITY.md) to learn about reliability features
- Check the main [README.md](../README.md) for usage examples
- Explore the [API Reference](API_REFERENCE.md) for detailed tool documentation
