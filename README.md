# IsoFinancial-MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/iso-financial-mcp.svg)](https://badge.fury.io/py/iso-financial-mcp)

An open-source MCP (Model Context Protocol) server providing comprehensive financial market data endpoints for short squeeze detection and analysis. Uses free financial data APIs including Yahoo Finance and other public sources.

## 🚀 Features

- **Real-time Market Data**: Live stock prices, volume, and market statistics
- **Financial Statements**: Balance sheets, income statements, and cash flow data
- **Options Analysis**: Option chains, expiration dates, and options data
- **Corporate Actions**: Dividends, stock splits, and earnings calendars
- **Company Information**: Company profiles, major holders, and institutional investors
- **Analyst Recommendations**: Professional analyst ratings and recommendations

## 📋 Requirements

- Python 3.10+
- uv (recommended package manager)
- Internet connection for API access

## 🔧 Installation

### Using uv (Recommended)

```bash
uv add iso-financial-mcp
```

### Using pip

```bash
pip install iso-financial-mcp
```

## 🚀 Quick Start

### As MCP Server (for AI agents)

```python
from fastmcp.agent import StdioServerParams, mcp_server_tools

# Configure the MCP server
finance_server_params = StdioServerParams(
    command="python",
    args=["-m", "server"],
    cwd="./IsoFinancial-MCP"
)

# Get available tools
finance_tools = await mcp_server_tools(finance_server_params)
```

### As HTTP Server

```bash
# Start HTTP server
python main.py --mode http --port 8000

# Or with uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 📊 Available Endpoints

### Market Data
- `get_info(ticker)` - Company profile and basic information
- `get_historical_prices(ticker, period, interval)` - Historical price data

### Financial Data
- `get_balance_sheet(ticker, freq)` - Balance sheet data
- `get_financials(ticker, freq)` - Income statement data
- `get_cash_flow(ticker, freq)` - Cash flow statement

### Options Analysis
- `get_options_expirations(ticker)` - Available expiration dates
- `get_option_chain(ticker, expiration_date)` - Complete option chain

### Corporate Actions
- `get_actions(ticker)` - Dividends and stock splits
- `get_earnings_dates(ticker)` - Earnings calendar

### Company Information
- `get_major_holders(ticker)` - Major shareholders
- `get_institutional_holders(ticker)` - Institutional holdings
- `get_recommendations(ticker)` - Analyst recommendations
- `get_isin(ticker)` - ISIN code

### Short Interest Analysis (COMING SOON)
- `get_short_interest(ticker)` - Current short interest data
- `get_short_interest_history(ticker, lookback)` - Historical short interest
- `get_days_to_cover(ticker)` - Days to cover calculation
- `get_cost_to_borrow(ticker)` - Current borrowing costs

### Volume Analysis (COMING SOON)
- `get_short_volume_daily(ticker, date)` - Daily short volume (FINRA)
- `get_short_volume_intraday(ticker, date)` - Intraday short volume
- `get_short_exempt_volume_daily(ticker, date)` - Short exempt volume

### Dark Pool & FTD Data (COMING SOON)
- `get_dark_pool_volume_daily(ticker, date)` - Daily dark pool volume
- `get_fail_to_deliver(ticker, from_date, to_date)` - Fail-to-deliver data

### Advanced Options Analysis (COMING SOON)
- `get_option_oi_by_strike(ticker, expiry)` - Open interest by strike
- `get_gamma_exposure(ticker, date)` - Gamma exposure calculation
- `get_max_pain(ticker, expiry)` - Max pain calculation

### Screening Tools (COMING SOON)
- `get_high_short_interest_tickers(threshold, limit)` - High SI tickers
- `get_latest_price(ticker)` - Current stock price
- `get_free_float(ticker)` - Free float data
- `get_company_profile(ticker)` - Detailed company profile
- `get_earnings_calendar(ticker, window)` - Earnings calendar
- `ping()` - Connectivity test

## 📖 Usage Examples

### Basic Market Data

```python
# Get company information
info = await get_info("AAPL")

# Get historical prices
prices = await get_historical_prices("TSLA", period="6mo", interval="1d")

# Get current price
price = await get_latest_price("GME")
```

### Financial Analysis

```python
# Get balance sheet
balance = await get_balance_sheet("AAPL", freq="yearly")

# Get income statement
income = await get_financials("TSLA", freq="quarterly")

# Get cash flow
cashflow = await get_cash_flow("MSFT", freq="yearly")
```

### Options Analysis

```python
# Get option expirations
expirations = await get_options_expirations("SPY")

# Get option chain
chain = await get_option_chain("SPY", "2024-01-19")
```

### Corporate Actions

```python
# Get dividends and splits
actions = await get_actions("AAPL")

# Get earnings dates
earnings = await get_earnings_dates("TSLA")
```

### Company Information

```python
# Get major shareholders
holders = await get_major_holders("GME")

# Get institutional investors
institutional = await get_institutional_holders("AAPL")

# Get analyst recommendations
recommendations = await get_recommendations("TSLA")
```

## 🔧 Configuration

The server uses free APIs by default (Yahoo Finance). No API keys are required for basic functionality.

```bash
# Copy environment template (optional)
cp .env.example .env

# No API keys needed for current features
# All data is sourced from Yahoo Finance (free)
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=datasources
```

## 📦 Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Format code
black .
ruff check .

# Type checking
mypy .
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Yahoo Finance](https://finance.yahoo.com/) for market data
- [FastMCP](https://github.com/fastmcp/fastmcp) for the MCP framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Niels-8/isofinancial-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Niels-8/isofinancial-mcp/discussions)

---

**Disclaimer**: This software is for educational and research purposes only. Always verify data independently before making investment decisions. 