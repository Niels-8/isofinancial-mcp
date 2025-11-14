# IsoFinancial-MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/iso-financial-mcp.svg)](https://badge.fury.io/py/iso-financial-mcp)
[![UV Package Manager](https://img.shields.io/badge/uv-package%20manager-blue.svg)](https://docs.astral.sh/uv/)

An enhanced open-source MCP (Model Context Protocol) server providing comprehensive financial market data endpoints for quantitative trading opportunity detection and analysis. Features advanced data sources including SEC filings, FINRA short volume, earnings calendars, news sentiment, and Google Trends analysis.

## 🚀 Enhanced Features

### Core Market Data (Yahoo Finance)
- **Real-time Market Data**: Live stock prices, volume, and market statistics
- **Financial Statements**: Balance sheets, income statements, and cash flow data
- **Options Analysis**: Complete option chains with expiration dates and Greeks
- **Corporate Actions**: Dividends, stock splits, and historical actions
- **Company Information**: Detailed profiles, major holders, and institutional investors
- **Analyst Recommendations**: Professional analyst ratings and price targets

### 🆕 Enhanced Data Sources for Quantitative Analysis
- **SEC Filings Integration**: Real-time EDGAR API access for 8-K, S-3, 424B, 10-Q, 10-K filings with 6-hour caching
- **FINRA Short Volume**: Daily short volume ratios and pressure indicators with trend analysis
- **Earnings Calendar**: EPS estimates, actuals, surprise percentages with BMO/AMC timing
- **News Headlines**: Yahoo Finance RSS integration with source attribution and duplicate detection
- **Google Trends**: Search volume analysis with momentum indicators and related queries
  - **Multi-source strategy**: SerpAPI (if configured) → DuckDuckGo (free) → PyTrends (fallback)
  - **Note**: PyTrends often fails with 429 errors; DuckDuckGo provides reliable estimated trends
  - See [TRENDS_SOURCES.md](docs/TRENDS_SOURCES.md) for detailed source comparison

### 🔧 Advanced Technical Features
- **Intelligent Caching**: Multi-tier caching system with configurable TTL per data source
- **Rate Limiting**: Built-in rate limiting with exponential backoff for API protection
- **Error Handling**: Graceful degradation with detailed error reporting
- **Performance Optimization**: Async/await throughout with connection pooling
- **Data Validation**: Comprehensive input validation and sanitization

## 🎯 Meta-Tools for Agent Optimization

**NEW in v0.3.0**: Consolidated meta-tools designed specifically for LLM agents with iteration budgets. These tools dramatically reduce the number of API calls needed, ensuring your agents can generate complete reports without running out of iterations.

### Why Meta-Tools?

Traditional approach requires **10-15 individual calls per ticker**, consuming precious agent iterations:
```python
# ❌ OLD WAY: 7+ separate calls per ticker
info = await get_info("AAPL")
prices = await get_historical_prices("AAPL")
news = await get_news_headlines("AAPL")
sec = await get_sec_filings("AAPL")
earnings = await get_earnings_calendar("AAPL")
short = await get_finra_short_volume("AAPL")
trends = await get_google_trends("AAPL")
# For 3 tickers: 21+ calls = 25+ agent iterations ❌
```

Meta-tools consolidate everything into **1-2 calls total**:
```python
# ✅ NEW WAY: 1 call for everything
analysis = await get_multi_ticker_analysis("AAPL,MSFT,GOOGL")
# All data for 3 tickers in parallel = 1-2 agent iterations ✅
```

### Available Meta-Tools

#### 🎯 `get_ticker_complete_analysis`
Get **ALL financial data** for a single ticker in one call.

```bash
# Single comprehensive call
uv run python -c "
from iso_financial_mcp.server import get_ticker_complete_analysis
import asyncio
result = asyncio.run(get_ticker_complete_analysis('AAPL', lookback_days=30))
print(result)
"
```

**Includes:**
- Company information (sector, industry, market cap)
- Historical prices (last 5 days + 30-day change)
- Recent news (5 articles with summaries)
- SEC filings (3 most recent)
- Earnings data (next + 3 recent quarters)
- FINRA short volume (aggregated metrics)
- Google Trends (search momentum)

**Parameters:**
- `ticker` (str): Stock symbol (e.g., "AAPL")
- `include_options` (bool): Include options data (default: False)
- `lookback_days` (int): Historical data window (default: 30)

#### 🎯 `get_multi_ticker_analysis`
Analyze **multiple tickers in parallel** with a single call.

```bash
# Parallel analysis of multiple tickers
uv run python -c "
from iso_financial_mcp.server import get_multi_ticker_analysis
import asyncio
result = asyncio.run(get_multi_ticker_analysis('NVDA,AMD,INTC', lookback_days=30))
print(result)
"
```

**Features:**
- Parallel data retrieval (5-10x faster than sequential)
- Automatic ticker limit (max 10 to prevent timeouts)
- Graceful error handling per ticker
- Pre-formatted, compact output optimized for LLMs

**Parameters:**
- `tickers` (str): Comma-separated ticker symbols (e.g., "AAPL,MSFT,GOOGL")
- `include_options` (bool): Include options data (default: False)
- `lookback_days` (int): Historical data window (default: 30)

### Performance Comparison

| Scenario | Before (Individual Tools) | After (Meta-Tools) | Improvement |
|----------|--------------------------|-------------------|-------------|
| **Single Ticker Analysis** | 7 calls, ~15s | 1 call, ~3s | **5x faster** |
| **3 Tickers Analysis** | 21 calls, ~45s | 1 call, ~5s | **9x faster** |
| **5 Tickers Analysis** | 35 calls, ~75s | 1 call, ~7s | **10x+ faster** |
| **Agent Iterations** | 25+ iterations | <20 iterations | **Guaranteed HTML** |
| **Token Consumption** | ~10,000 tokens | ~3,000 tokens | **70% reduction** |

### Real-World Example: Newsletter Generation

**Before Meta-Tools (❌ Often fails to generate HTML):**
```
Iteration 1-7:   Analyze NVDA (7 individual calls)
Iteration 8-14:  Analyze AMD (7 individual calls)
Iteration 15-21: Analyze INTC (7 individual calls)
Iteration 22-25: Try to start HTML generation...
Iteration 26+:   ❌ TIMEOUT - No report generated
```

**After Meta-Tools (✅ Always generates HTML):**
```
Iteration 1-2:   get_multi_ticker_analysis("NVDA,AMD,INTC")
                 → All data retrieved in parallel
Iteration 3:     Analyze consolidated results
Iteration 4-15:  Generate comprehensive HTML report ✅
Iteration 16+:   Refinements (optional)
```

### Token Optimization

Meta-tools return **pre-formatted, compact data** optimized for LLM consumption:

- **Company summaries**: Truncated to 300 chars (vs 500+ words)
- **Historical prices**: Last 5 days only (vs 30 days)
- **News articles**: 5 articles max, 150 char summaries
- **SEC filings**: 3 most recent only
- **Earnings**: Next + 3 recent quarters only
- **Aggregated metrics**: Summary stats vs raw data

**Result**: 50-70% token reduction while maintaining data quality.

### Integration with AI Agents

Perfect for agents with iteration budgets (e.g., newsletter generators, trading analysts):

```python
# Example: Newsletter agent with 30 iteration budget
from iso_financial_mcp.server import get_multi_ticker_analysis

# Reserve 10 iterations for HTML generation
# Use meta-tools for data gathering (1-2 iterations)
async def generate_newsletter(tickers: list):
    # Single call gets ALL data
    analysis = await get_multi_ticker_analysis(",".join(tickers))
    
    # Agent now has 25+ iterations left for:
    # - Analysis and insights
    # - HTML report generation
    # - Refinements and polish
    
    return analysis
```

### Migration from Individual Tools

Migrating from individual tools to meta-tools is straightforward:

**Before (Individual Tools):**
```python
# Multiple separate calls
info = await get_info("AAPL")
prices = await get_historical_prices("AAPL")
news = await get_news_headlines("AAPL")
# ... 7+ more calls
```

**After (Meta-Tools):**
```python
# Single consolidated call
analysis = await get_ticker_complete_analysis("AAPL")
# All data retrieved in parallel
```

**Best Practices:**
- Use `get_ticker_complete_analysis` for single ticker deep dives
- Use `get_multi_ticker_analysis` for comparing multiple tickers
- Set `include_options=False` to reduce token usage if options data not needed
- Adjust `lookback_days` based on your analysis needs (default: 30)

**Note**: All individual tools remain available for backward compatibility, but meta-tools are strongly recommended for agent-based workflows.

## 📋 Requirements

- **Python 3.10+** (Python 3.13+ recommended for optimal performance)
- **UV Package Manager** ([Installation Guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Internet connection** for API access to multiple data sources
- **No API keys required** - All data sources use free/public APIs

## 🔧 Installation

### Using UV (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to your project
uv add iso-financial-mcp

# Or install globally
uvx iso-financial-mcp
```

### Using pip

```bash
pip install iso-financial-mcp
```

### For AI Trading Systems Integration

The IsoFinancial-MCP server can be easily integrated into any AI trading system or quantitative analysis pipeline:

```bash
# Add to your trading system dependencies
uv add iso-financial-mcp

# Or include in your pyproject.toml
dependencies = ["iso-financial-mcp>=0.2.0"]
```

## 🚀 Quick Start

### As MCP Server (Recommended for AI Agents)

```bash
# Test the server directly
uv run python -m iso_financial_mcp

# Or run specific endpoints
uv run python -c "
from iso_financial_mcp.server import get_info
import asyncio
result = asyncio.run(get_info('AAPL'))
print(result)
"
```

### Integration with AI Trading Systems

The server can be easily integrated with any AI trading system or quantitative analysis framework:

```python
# Example integration with MCP-compatible AI agents
from fastmcp.agent import StdioServerParams, mcp_server_tools

finance_server_params = StdioServerParams(
    command="python",
    args=["-m", "iso_financial_mcp"],
)

# Get available financial tools
finance_tools = await mcp_server_tools(finance_server_params)
```

### As Standalone HTTP Server

```bash
# Start HTTP server with UV
uv run uvicorn iso_financial_mcp.server:server.app --host 0.0.0.0 --port 8000

# Test endpoints
curl http://localhost:8000/health
```

### Testing Individual Endpoints

```bash
# Test SEC filings
uv run python -c "
from iso_financial_mcp.server import get_sec_filings
import asyncio
result = asyncio.run(get_sec_filings('AAPL', '8-K,S-3', 30))
print(result)
"

# Test FINRA short volume
uv run python -c "
from iso_financial_mcp.server import get_finra_short_volume
import asyncio
result = asyncio.run(get_finra_short_volume('GME'))
print(result)
"

# Test earnings calendar
uv run python -c "
from iso_financial_mcp.server import get_earnings_calendar
import asyncio
result = asyncio.run(get_earnings_calendar('NVDA'))
print(result)
"
```

## 📊 Available Endpoints

### 📈 Core Market Data (Yahoo Finance)
- `get_info(ticker)` - Company profile and basic information
- `get_historical_prices(ticker, period, interval)` - Historical price data with OHLCV
- `get_actions(ticker)` - Dividends and stock splits history
- `get_earnings_dates(ticker)` - Upcoming and historical earnings dates
- `get_isin(ticker)` - International Securities Identification Number

### 💰 Financial Statements
- `get_balance_sheet(ticker, freq)` - Balance sheet data (yearly/quarterly)
- `get_financials(ticker, freq)` - Income statement data (yearly/quarterly)
- `get_cash_flow(ticker, freq)` - Cash flow statement (yearly/quarterly)

### 📊 Options Analysis
- `get_options_expirations(ticker)` - Available expiration dates
- `get_option_chain(ticker, expiration_date)` - Complete option chain with Greeks

### 🏢 Company Information
- `get_major_holders(ticker)` - Major shareholders and insider holdings
- `get_institutional_holders(ticker)` - Institutional investor positions
- `get_recommendations(ticker)` - Analyst recommendations and price targets

### 🆕 Enhanced Data Sources for Quantitative Analysis

#### 📋 SEC Filings (EDGAR API)
```python
get_sec_filings(ticker, form_types="8-K,S-3,424B,10-Q,10-K", lookback_days=30)
```
- **Form Types**: 8-K (material events), S-3 (shelf registrations), 424B (prospectus), 10-Q/10-K (quarterly/annual reports)
- **Cache TTL**: 6 hours
- **Features**: Direct EDGAR API integration, accession numbers, filing URLs

#### 📊 FINRA Short Volume
```python
get_finra_short_volume(ticker, start_date="", end_date="")
```
- **Data Source**: FINRA daily short volume CSV files
- **Cache TTL**: 24 hours
- **Features**: Short ratios, trend analysis, aggregate metrics, 5-day rolling averages

#### 📅 Earnings Calendar
```python
get_earnings_calendar(ticker)
```
- **Data Source**: Yahoo Finance/Nasdaq earnings data
- **Cache TTL**: 24 hours
- **Features**: EPS estimates, actuals, surprise percentages, BMO/AMC timing, upcoming vs historical

#### 📰 News Headlines
```python
get_news_headlines(ticker, limit=10, lookback_days=3)
```
- **Data Source**: Yahoo Finance RSS feeds
- **Cache TTL**: 2 hours
- **Features**: Source attribution, duplicate detection, summary extraction, publication timestamps

#### 📈 Google Trends
```python
get_google_trends(term, window_days=30)
```
- **Data Sources** (priority order):
  1. **SerpAPI** (if configured): Full Google Trends data, highly reliable
  2. **DuckDuckGo** (default): Estimated trends, free and reliable
  3. **PyTrends** (fallback): Full data but often fails with 429 errors
- **Cache TTL**: 24 hours
- **Features**: Search volume trends, momentum analysis, related queries (SerpAPI/PyTrends only)
- **Configuration**: Set `SERPAPI_KEY` for best results, or rely on free DuckDuckGo
- **See**: [TRENDS_SOURCES.md](docs/TRENDS_SOURCES.md) for detailed comparison

### 🔧 Technical Features

#### Caching System
- **Multi-tier caching** with configurable TTL per endpoint
- **Memory-efficient** with automatic cleanup
- **Cache warming** for frequently accessed data

#### Rate Limiting
- **Per-endpoint rate limiting** with exponential backoff
- **Burst protection** with token bucket algorithm
- **API-specific limits** respecting provider constraints

#### Error Handling
- **Graceful degradation** when data sources are unavailable
- **Detailed error reporting** with context and suggestions
- **Automatic retries** with intelligent backoff strategies

## 📖 Usage Examples

### Basic Market Data

```bash
# Get company information
uv run python -c "
from iso_financial_mcp.server import get_info
import asyncio
result = asyncio.run(get_info('AAPL'))
print(result)
"

# Get historical prices with custom period
uv run python -c "
from iso_financial_mcp.server import get_historical_prices
import asyncio
result = asyncio.run(get_historical_prices('TSLA', '6mo', '1d'))
print(result)
"
```

### Financial Analysis

```bash
# Get quarterly financials
uv run python -c "
from iso_financial_mcp.server import get_financials
import asyncio
result = asyncio.run(get_financials('NVDA', 'quarterly'))
print(result)
"

# Get balance sheet
uv run python -c "
from iso_financial_mcp.server import get_balance_sheet
import asyncio
result = asyncio.run(get_balance_sheet('AAPL', 'yearly'))
print(result)
"
```

### Options Analysis

```bash
# Get option expirations
uv run python -c "
from iso_financial_mcp.server import get_options_expirations
import asyncio
result = asyncio.run(get_options_expirations('SPY'))
print(result)
"

# Get complete option chain
uv run python -c "
from iso_financial_mcp.server import get_option_chain
import asyncio
result = asyncio.run(get_option_chain('SPY', '2024-12-20'))
print(result)
"
```

### 🆕 Enhanced Data Sources

#### SEC Filings Analysis

```bash
# Get recent 8-K and S-3 filings
uv run python -c "
from iso_financial_mcp.server import get_sec_filings
import asyncio
result = asyncio.run(get_sec_filings('GME', '8-K,S-3', 30))
print(result)
"

# Get all major filing types
uv run python -c "
from iso_financial_mcp.server import get_sec_filings
import asyncio
result = asyncio.run(get_sec_filings('AAPL', '8-K,S-3,424B,10-Q,10-K', 60))
print(result)
"
```

#### FINRA Short Volume Analysis

```bash
# Get short volume with trend analysis
uv run python -c "
from iso_financial_mcp.server import get_finra_short_volume
import asyncio
result = asyncio.run(get_finra_short_volume('AMC'))
print(result)
"

# Get short volume for specific date range
uv run python -c "
from iso_financial_mcp.server import get_finra_short_volume
import asyncio
result = asyncio.run(get_finra_short_volume('GME', '2024-01-01', '2024-01-31'))
print(result)
"
```

#### Earnings Calendar with Surprises

```bash
# Get comprehensive earnings data
uv run python -c "
from iso_financial_mcp.server import get_earnings_calendar
import asyncio
result = asyncio.run(get_earnings_calendar('NVDA'))
print(result)
"

# Analyze earnings surprises
uv run python -c "
from iso_financial_mcp.server import get_earnings_calendar
import asyncio
result = asyncio.run(get_earnings_calendar('TSLA'))
print(result)
"
```

#### News Sentiment Analysis

```bash
# Get recent news headlines
uv run python -c "
from iso_financial_mcp.server import get_news_headlines
import asyncio
result = asyncio.run(get_news_headlines('AAPL', 15, 5))
print(result)
"

# Monitor breaking news
uv run python -c "
from iso_financial_mcp.server import get_news_headlines
import asyncio
result = asyncio.run(get_news_headlines('TSLA', 5, 1))
print(result)
"
```

#### Google Trends Social Momentum

```bash
# Analyze search trends for ticker
uv run python -c "
from iso_financial_mcp.server import get_google_trends
import asyncio
result = asyncio.run(get_google_trends('GameStop', 30))
print(result)
"

# Monitor company name trends
uv run python -c "
from iso_financial_mcp.server import get_google_trends
import asyncio
result = asyncio.run(get_google_trends('Tesla Motors', 60))
print(result)
"
```

### Integration with AI Trading Agents

The IsoFinancial-MCP server can be integrated with any MCP-compatible AI trading agent:

```python
# Example: Using with AI trading agents
from your_trading_agent import TradingAgent

agent = TradingAgent()
agent.add_mcp_server("iso-financial-mcp")

# Agent can now use all financial endpoints
# Example agent query: "Get SEC filings and short volume data for GME"
```

## 🔧 Configuration

### No API Keys Required

The server uses entirely free and public APIs:
- **Yahoo Finance**: Market data, financials, options (no authentication)
- **SEC EDGAR**: Official SEC filings API (public access)
- **FINRA**: Daily short volume CSV files (public data)
- **Google Trends**: Multi-source (DuckDuckGo free, SerpAPI optional, PyTrends fallback)
- **RSS Feeds**: News headlines from Yahoo Finance RSS (public)

### Optional Configuration

```bash
# Copy environment template (optional for advanced configuration)
cp .env.example .env
```

### Cache Configuration

Default cache TTL settings optimized for trading applications:

```python
CACHE_TTL = {
    'sec_filings': 21600,    # 6 hours - SEC filings don't change frequently
    'finra_data': 86400,     # 24 hours - FINRA data is daily
    'earnings': 86400,       # 24 hours - Earnings calendar updates daily
    'news': 7200,            # 2 hours - News updates frequently
    'trends': 86400,         # 24 hours - Trends data is daily
    'market_data': 300,      # 5 minutes - Market data for real-time needs
    'options_data': 900      # 15 minutes - Options data updates frequently
}
```

### Rate Limiting Configuration

Built-in rate limiting respects API provider limits:

```python
RATE_LIMITS = {
    'yahoo_finance': {'calls_per_minute': 120, 'burst_limit': 20},
    'sec_edgar': {'calls_per_minute': 10, 'burst_limit': 3},
    'google_trends': {'calls_per_minute': 20, 'burst_limit': 5},
    'rss_feeds': {'calls_per_minute': 60, 'burst_limit': 10}
}
```

### Integration with Trading Systems

When integrated with AI trading systems, configuration can be handled automatically:

```python
# Example: Automatic configuration in trading systems
from iso_financial_mcp.server import server

# Server can be embedded directly in your application
app = YourTradingApp()
app.add_mcp_server(server)  # All endpoints available automatically
```

## 🧪 Testing

### Comprehensive Test Suite

```bash
# Run all tests with UV
uv run pytest

# Run with coverage reporting
uv run pytest --cov=iso_financial_mcp --cov-report=html

# Run specific test categories
uv run pytest tests/test_yfinance_source.py    # Yahoo Finance endpoints
uv run pytest tests/test_sec_source.py         # SEC filings
uv run pytest tests/test_finra_source.py       # FINRA short volume
uv run pytest tests/test_earnings_source.py    # Earnings calendar
uv run pytest tests/test_news_source.py        # News headlines
uv run pytest tests/test_trends_source.py      # Google Trends

# Integration tests
uv run pytest tests/test_integration.py        # End-to-end testing
```

### Manual Testing

```bash
# Test individual endpoints
uv run python -c "
from iso_financial_mcp.server import get_info, get_sec_filings, get_finra_short_volume
import asyncio

async def test_endpoints():
    # Test basic market data
    info = await get_info('AAPL')
    print('✅ Basic info:', 'OK' if info else 'FAILED')
    
    # Test SEC filings
    filings = await get_sec_filings('AAPL', '8-K', 30)
    print('✅ SEC filings:', 'OK' if 'SEC Filings' in filings else 'FAILED')
    
    # Test FINRA data
    short_data = await get_finra_short_volume('GME')
    print('✅ FINRA data:', 'OK' if 'Short Volume Data' in short_data else 'FAILED')

asyncio.run(test_endpoints())
"

# Test server startup
uv run python -m iso_financial_mcp
```

### Performance Testing

```bash
# Test with high-volume tickers
uv run python -c "
import asyncio
import time
from iso_financial_mcp.server import get_info

async def performance_test():
    tickers = ['AAPL', 'TSLA', 'NVDA', 'GME', 'AMC']
    start_time = time.time()
    
    tasks = [get_info(ticker) for ticker in tickers]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    print(f'Processed {len(tickers)} tickers in {end_time - start_time:.2f} seconds')
    print(f'Average: {(end_time - start_time) / len(tickers):.2f} seconds per ticker')

asyncio.run(performance_test())
"
```

## 📦 Development

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Niels-8/isofinancial-mcp.git
cd isofinancial-mcp

# Install with development dependencies using UV
uv sync --dev

# Or install in editable mode
uv pip install -e ".[dev]"
```

### Code Quality Tools

```bash
# Format code with Black
uv run black .

# Lint with Ruff
uv run ruff check . --fix

# Type checking with MyPy
uv run mypy .

# Run all quality checks
uv run black . && uv run ruff check . && uv run mypy .
```

### Adding New Data Sources

1. **Create Data Source Module**: Add new module in `iso_financial_mcp/datasources/`
2. **Implement Async Functions**: Follow existing patterns with caching and error handling
3. **Add Server Endpoint**: Register new endpoint in `server.py` with `@server.tool` decorator
4. **Write Tests**: Add comprehensive tests in `tests/` directory
5. **Update Documentation**: Update README with new endpoint documentation

### Example: Adding New Data Source

```python
# iso_financial_mcp/datasources/new_source.py
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
from ..utils.cache import cached_request
from ..utils.rate_limiter import rate_limit

@rate_limit('new_api', calls_per_minute=60)
@cached_request(ttl=3600)  # 1 hour cache
async def get_new_data(ticker: str) -> Optional[Dict[str, Any]]:
    """Get data from new source"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.newsource.com/data/{ticker}"
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        print(f"Error fetching new data for {ticker}: {e}")
        return None

# server.py - Add endpoint
@server.tool
async def get_new_endpoint(ticker: str) -> str:
    """Get new data endpoint"""
    data = await new_source.get_new_data(ticker)
    return format_data(data) if data else f"No data for {ticker}"
```

### Building and Publishing

```bash
# Build package
uv build

# Check package
uv run twine check dist/*

# Publish to PyPI (maintainers only)
uv run twine upload dist/*
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Integration with AI Trading Systems

This MCP server is designed to work seamlessly with any quantitative trading system or AI agent:

### Easy Integration
- **Zero Configuration**: Simple setup with any MCP-compatible system
- **Optimized Caching**: Cache TTL settings optimized for trading workflows
- **Error Handling**: Graceful degradation ensures systems continue working even if some data sources fail

### Supported Trading Opportunity Types
The enhanced endpoints support detection of multiple opportunity types:
1. **Short Squeeze Analysis**: FINRA short volume + SEC filings + social trends
2. **Breakout/Momentum Detection**: News sentiment + Google Trends + volume analysis
3. **Earnings Plays**: Earnings calendar + EPS surprises + options data
4. **Biotech/FDA Events**: SEC 8-K filings + news headlines + social momentum
5. **M&A/Rumor Detection**: News analysis + social trends + volume spikes
6. **Dilution/ATM Detection**: SEC S-3/424B filings + volume analysis
7. **Gap-Fade Opportunities**: News sentiment + volume patterns + options data

### Usage in Trading Systems
```python
# Example: Integration with AI trading agents
from your_trading_system import TradingAgent

agent = TradingAgent()
agent.add_financial_data_source("iso-financial-mcp")

# Agent can now use IsoFinancial-MCP for:
# - SEC filing analysis for dilution detection
# - FINRA short volume for squeeze signals
# - Earnings calendar for earnings plays
# - News sentiment for momentum analysis
# - Google Trends for social validation
```

## 🙏 Acknowledgments

- **[Yahoo Finance](https://finance.yahoo.com/)** for comprehensive market data
- **[SEC EDGAR](https://www.sec.gov/edgar)** for official filing data
- **[FINRA](https://www.finra.org/)** for short volume transparency
- **[Google Trends](https://trends.google.com/)** for search volume insights
- **[FastMCP](https://github.com/fastmcp/fastmcp)** for the MCP framework
- **[UV Package Manager](https://docs.astral.sh/uv/)** for modern Python packaging
- **Open Source Community** for contributions and feedback

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Niels-8/isofinancial-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Niels-8/isofinancial-mcp/discussions)

## 📊 Data Sources & Reliability

### Data Source Overview
| Data Source | Endpoint | Update Frequency | Cache TTL | Fallback Sources | Reliability |
|-------------|----------|------------------|-----------|------------------|-------------|
| Yahoo Finance | Market data, financials, options | Real-time to daily | 5min-24h | N/A | High |
| SEC EDGAR | Official filings | Real-time | 6 hours | RSS Feed, XBRL API | Very High |
| FINRA | Short volume | Daily | 24 hours | N/A | High |
| Google Trends | Search volume | Daily | 24 hours | DuckDuckGo, SerpAPI | Medium-High |
| Earnings | Calendar data | Daily | 24 hours | Nasdaq, Alpha Vantage | High |
| RSS Feeds | News headlines | Hourly | 2 hours | N/A | Medium |

### 🛡️ Reliability Features (v0.4.0+)

#### Multi-Source Fallback
Automatic fallback to alternative data sources when primary sources fail:

- **SEC Filings**: EDGAR API → RSS Feed → XBRL API → Stale Cache
- **Google Trends**: SerpAPI (if configured) → DuckDuckGo → PyTrends → Stale Cache
- **Earnings**: Yahoo Finance → Nasdaq API → Alpha Vantage → Estimation

#### Intelligent Caching
Two-level caching system with stale data fallback:

- **Memory Cache**: Fast in-memory cache (1 hour TTL, 1000 items)
- **Disk Cache**: Persistent disk cache (7 days TTL, 500MB max)
- **Stale Fallback**: Returns expired cache when all sources fail
- **Automatic Cleanup**: Old cache entries are automatically purged

#### Adaptive Rate Limiting
Smart rate limiting that adjusts to API behavior:

- **Error Detection**: Monitors 429 rate limit errors
- **Exponential Backoff**: 10s → 20s → 40s delays with jitter
- **Slow Mode**: Automatically activates when error rate >50%
- **Per-Source Limits**: Independent rate limiting for each API

#### Health Monitoring
Continuous monitoring of data source reliability:

- **Success Rate Tracking**: Monitors last 100 requests per source
- **Automatic Failover**: Skips sources with <30% success rate
- **Metrics Logging**: JSONL logs for debugging and analysis
- **Health Status API**: Query source health programmatically

#### Graceful Degradation
System continues working even when sources fail:

- **Partial Data**: Returns available data with error details
- **Error Classification**: Distinguishes temporary vs permanent errors
- **Actionable Messages**: Suggests fixes for common issues
- **No Silent Failures**: All errors are logged and reported

### Configuration

#### Default Configuration (No Setup Required)
The system works out-of-the-box with sensible defaults. No configuration needed!

#### Custom Configuration (Optional)
For advanced users, create `~/.iso_financial_mcp/config/datasources.yaml`:

```yaml
# Example: Adjust rate limiting for Google Trends
trends:
  sources:
    - name: pytrends_direct
      enabled: true
      rate_limit: 0.1  # Slower: 1 req / 10 sec
  
  adaptive_rate_limit:
    enabled: true
    error_threshold: 0.5
    slow_mode_delay: 10

# Example: Enable optional sources with API keys
earnings:
  sources:
    - name: alpha_vantage
      enabled: true
      api_key_env: ALPHA_VANTAGE_KEY  # Set via environment variable
```

See `config/datasources.yaml.example` for full configuration options.

#### Environment Variables
Optional API keys for enhanced data sources:

```bash
# Alpha Vantage (for additional earnings data)
export ALPHA_VANTAGE_KEY="your_key_here"

# SerpAPI (for Google Trends fallback)
export SERPAPI_KEY="your_key_here"
```

### Data Quality Features
- **Duplicate Detection**: News headlines are deduplicated across sources
- **Data Validation**: Input validation and sanitization for all endpoints
- **Error Recovery**: Graceful fallback when data sources are unavailable
- **Cache Warming**: Frequently accessed data is pre-cached
- **Rate Limiting**: Respects API provider limits to ensure consistent access
- **Data Fusion**: Merges data from multiple sources for better coverage
- **Automatic Retry**: Intelligent retry with exponential backoff

---

## 🔧 MCP Configuration Tools

**NEW in v0.4.0**: Configure the server directly through MCP tools without editing configuration files.

### Available Configuration Tools

#### `configure_api_key`
Configure API keys for optional data sources at runtime.

```python
# Configure Alpha Vantage for enhanced earnings data
await configure_api_key("alpha_vantage", "YOUR_API_KEY_HERE")

# Configure SerpAPI for Google Trends fallback
await configure_api_key("serpapi", "YOUR_API_KEY_HERE")
```

**Features:**
- Validates API keys before saving
- Persists configuration for future sessions
- Provides clear success/error messages
- Supports: `alpha_vantage`, `serpapi`

#### `get_configuration`
View current configuration with masked API keys.

```python
# Get current configuration
await get_configuration()
```

**Returns:**
- API keys (masked for security: `...XXXX`)
- Cache settings (TTL, max size)
- Rate limit configuration
- Enabled data sources

#### `list_data_sources`
List all available data sources and their status.

```python
# List all data sources
await list_data_sources()
```

**Shows:**
- ✅ Enabled sources (no API key required)
- ⚠️ Disabled sources (API key required but not configured)
- Source descriptions and capabilities

### Configuration Methods

The server supports three configuration methods with priority order:

1. **MCP Tools** (Highest Priority) - Runtime configuration via `configure_api_key`
2. **Environment Variables** - Set `ALPHA_VANTAGE_KEY`, `SERPAPI_KEY`, etc.
3. **YAML File** (Lowest Priority) - `~/.iso_financial_mcp/config/datasources.yaml`

See [Configuration Guide](docs/CONFIGURATION.md) for detailed examples.

---

## 🏥 MCP Health Check Tools

**NEW in v0.4.0**: Monitor data source health and diagnose issues through MCP tools.

### Available Health Check Tools

#### `get_health_status`
Get comprehensive health status for all data sources.

```python
# Check health of all sources
await get_health_status()
```

**Returns for each source:**
- ✅ Status: healthy / ⚠️ degraded / ❌ unhealthy
- Success rate (last 100 requests)
- Average latency (milliseconds)
- Total requests processed
- Last successful request timestamp
- Recent error messages (if any)

**Example Output:**
```
🏥 Data Sources Health Status:

✅ Yahoo Finance
   Status: healthy
   Success Rate: 98.5%
   Avg Latency: 245ms
   Total Requests: 1,234
   Last Success: 2025-01-15 14:32:10

⚠️ Google Trends
   Status: degraded
   Success Rate: 65.2%
   Avg Latency: 1,850ms
   Total Requests: 456
   Recent Errors: Rate limit exceeded, Timeout
```

#### `test_data_source`
Test a specific data source with a sample request.

```python
# Test SEC filings source
await test_data_source("sec", "AAPL")

# Test Google Trends source
await test_data_source("trends", "Tesla")

# Test earnings calendar
await test_data_source("earnings", "NVDA")
```

**Features:**
- Measures response time
- Shows data preview (first 500 chars)
- Provides detailed error messages
- Tests with real API calls

**Supported Sources:**
- `sec` - SEC EDGAR filings
- `trends` - Google Trends
- `earnings` - Earnings calendar
- `finra` - FINRA short volume
- `news` - News headlines

**Example Output:**
```
🧪 Testing sec with ticker AAPL...

✅ Test successful!
⏱️  Response time: 1.23s
📊 Data preview:
SEC Filings for AAPL (Last 30 days)
Found 3 filings:
1. 8-K - 2025-01-10 - Material Event...
```

### Use Cases

**Troubleshooting:**
```python
# Check if a source is having issues
status = await get_health_status()

# Test specific source that's failing
result = await test_data_source("trends", "AAPL")
```

**Monitoring:**
```python
# Regular health checks in production
status = await get_health_status()
# Alert if any source has <80% success rate
```

**Validation:**
```python
# Verify API key configuration
await configure_api_key("alpha_vantage", "YOUR_KEY")
await test_data_source("earnings", "AAPL")
```

---

## 📚 Documentation

For detailed information about the system, see our comprehensive documentation:

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design, components, and data flow
- **[Configuration Guide](docs/CONFIGURATION.md)** - How to configure API keys, caching, and rate limits
- **[Reliability Features](docs/RELIABILITY.md)** - Multi-source fallback, health monitoring, and error handling
- **[Changelog](CHANGELOG.md)** - Version history and release notes

---

## ⚠️ Important Disclaimers

**FINANCIAL DATA DISCLAIMER**: This software provides financial data for educational and research purposes only. The data is sourced from public APIs and may contain errors, delays, or inaccuracies. Always verify data independently before making investment decisions.

**TRADING RISK WARNING**: Trading involves substantial risk of loss and is not suitable for all investors. Past performance does not guarantee future results. The quantitative analysis provided by this system should not be considered as financial advice.

**DATA ACCURACY**: While we strive for accuracy, financial data can be subject to revisions, delays, and errors from source providers. Critical trading decisions should always be based on official sources and professional financial advice.

**NO WARRANTY**: This software is provided "as is" without warranty of any kind. The authors and contributors are not responsible for any financial losses resulting from the use of this software. 