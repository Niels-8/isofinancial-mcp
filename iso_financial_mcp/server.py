#!/usr/bin/env python3
"""
Finance MCP Server 
"""

from fastmcp.server.server import FastMCP
from typing import Optional, List
from datetime import datetime
import pandas as pd
import json
import warnings

# Suppress pandas FutureWarnings globally for the server
warnings.filterwarnings('ignore', category=FutureWarning, message='.*pandas.*')
warnings.filterwarnings('ignore', category=FutureWarning, message='.*count.*positional.*')
from .datasources import yfinance_source as yf_source
from .datasources import sec_source
from .datasources import finra_source
from .datasources import earnings_source
from .datasources import news_source
from .datasources import trends_source

# Import meta-tools for consolidated data retrieval
from .meta_tools import (
    get_financial_snapshot,
    get_multi_ticker_snapshot,
    format_snapshot_for_llm,
    format_multi_snapshot_for_llm
)

# Import configuration manager
from .reliability.configuration_manager import ConfigurationManager

# Instantiate the server first
server = FastMCP(
    name="IsoFinancial-MCP"
)

# Initialize configuration manager
config_manager = ConfigurationManager()

# --- Tool Definitions ---

def dataframe_to_string(df: Optional[pd.DataFrame]) -> str:
    """Converts a pandas DataFrame to a string, handling None cases."""
    if df is None:
        return "No data available."
    if isinstance(df, pd.Series):
        return df.to_string()
    return df.to_string()

# --- META-TOOLS (Consolidated Data Retrieval) ---

@server.tool
async def get_ticker_complete_analysis(
    ticker: str,
    include_options: bool = False,
    lookback_days: int = 30
) -> str:
    """
    🎯 META-TOOL: Récupère TOUTES les données financières d'un ticker en 1 seul appel.
    
    This consolidated tool fetches ALL financial data for a ticker in a single call,
    dramatically reducing LLM iterations and token consumption. It retrieves data from
    multiple sources in parallel and returns pre-formatted, compact results optimized
    for LLM analysis.
    
    Includes:
    - General company information (sector, industry, market cap, summary)
    - Historical price data with 30-day performance
    - Recent news headlines (last 5 articles)
    - SEC filings (8-K, 10-Q, 10-K)
    - Earnings calendar (upcoming + recent quarters)
    - FINRA short volume data with ratios
    - Google Trends search volume analysis
    - Options data (optional, increases token usage)
    
    :param ticker: The stock ticker symbol (e.g., 'AAPL', 'NVDA')
    :param include_options: Include options data (default: False, increases response size)
    :param lookback_days: Number of days for historical data (default: 30)
    
    :return: Formatted text with all financial data, optimized for LLM consumption
    
    Example Usage:
        # Single ticker analysis - replaces 7+ individual tool calls
        result = await get_ticker_complete_analysis("AAPL")
        
        # With options data
        result = await get_ticker_complete_analysis("NVDA", include_options=True)
        
        # Shorter lookback period for faster response
        result = await get_ticker_complete_analysis("MSFT", lookback_days=7)
    
    Performance:
        - Replaces 7+ individual tool calls with 1 consolidated call
        - 5-10x faster than sequential individual calls (parallel data fetching)
        - 50-70% token reduction through compact formatting
        - Graceful degradation if some data sources fail
    
    Note:
        This meta-tool is designed for LLM agents with iteration budgets.
        For multi-ticker analysis, use get_multi_ticker_analysis instead.
    """
    try:
        # Fetch all data in parallel using meta_tools
        snapshot = await get_financial_snapshot(
            ticker=ticker,
            include_options=include_options,
            lookback_days=lookback_days
        )
        
        # Format for LLM consumption (compact, token-optimized)
        formatted_result = format_snapshot_for_llm(snapshot)
        
        return formatted_result
        
    except Exception as e:
        error_msg = f"❌ Error analyzing {ticker}: {str(e)}\n\n"
        error_msg += "Possible causes:\n"
        error_msg += "- Invalid ticker symbol\n"
        error_msg += "- Network connectivity issues\n"
        error_msg += "- Data source temporarily unavailable\n\n"
        error_msg += "Suggestions:\n"
        error_msg += "- Verify the ticker symbol is correct\n"
        error_msg += "- Try again in a few moments\n"
        error_msg += "- Use individual tools (get_info, get_news, etc.) as fallback\n"
        
        return error_msg

@server.tool
async def get_multi_ticker_analysis(
    tickers: str,
    include_options: bool = False,
    lookback_days: int = 30
) -> str:
    """
    🎯 META-TOOL: Analyse PLUSIEURS tickers en parallèle (1 seul appel).
    
    This consolidated tool analyzes multiple tickers simultaneously in a single call,
    dramatically reducing LLM iterations. It fetches data for all tickers in parallel
    and returns pre-formatted, compact results optimized for LLM analysis.
    
    Perfect for:
    - Sector analysis (e.g., "NVDA,AMD,INTC" for semiconductor sector)
    - Portfolio analysis (multiple holdings at once)
    - Comparative analysis (competitors side-by-side)
    - Thematic newsletters (AI stocks, EV stocks, etc.)
    
    :param tickers: Comma-separated list of ticker symbols (e.g., 'AAPL,MSFT,GOOGL')
    :param include_options: Include options data for all tickers (default: False, increases response size)
    :param lookback_days: Number of days for historical data (default: 30)
    
    :return: Formatted text with all tickers' financial data, optimized for LLM consumption
    
    Example Usage:
        # Analyze 3 tech stocks - replaces 21+ individual tool calls
        result = await get_multi_ticker_analysis("AAPL,MSFT,GOOGL")
        
        # Semiconductor sector analysis
        result = await get_multi_ticker_analysis("NVDA,AMD,INTC,AVGO,QCOM")
        
        # Quick analysis with shorter lookback
        result = await get_multi_ticker_analysis("TSLA,F,GM", lookback_days=7)
    
    Performance:
        - Replaces 7+ individual tool calls PER TICKER with 1 consolidated call
        - For 3 tickers: 21+ calls → 1 call (21x reduction)
        - 5-10x faster than sequential individual calls (parallel data fetching)
        - 50-70% token reduction through compact formatting
        - Graceful degradation if some tickers or data sources fail
    
    Limits:
        - Maximum 10 tickers per call (to prevent timeouts)
        - If you provide more than 10, only the first 10 will be analyzed
        - For >10 tickers, make multiple calls or prioritize most important ones
    
    Note:
        This meta-tool is designed for LLM agents with iteration budgets.
        For single ticker analysis, use get_ticker_complete_analysis instead.
    """
    try:
        # Parse tickers from comma-separated string
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        if not ticker_list:
            return "❌ Error: No valid tickers provided. Please provide comma-separated ticker symbols (e.g., 'AAPL,MSFT,GOOGL')."
        
        # Inform user if we're limiting the number of tickers
        if len(ticker_list) > 10:
            limited_tickers = ticker_list[:10]
            warning_msg = f"⚠️ Note: Limiting analysis to first 10 tickers (provided {len(ticker_list)})\n"
            warning_msg += f"Analyzing: {', '.join(limited_tickers)}\n\n"
        else:
            warning_msg = ""
        
        # Fetch all ticker data in parallel using meta_tools
        multi_snapshot = await get_multi_ticker_snapshot(
            tickers=ticker_list,
            include_options=include_options,
            lookback_days=lookback_days,
            max_tickers=10
        )
        
        # Format for LLM consumption (compact, token-optimized)
        formatted_result = format_multi_snapshot_for_llm(multi_snapshot)
        
        # Prepend warning if we limited tickers
        if warning_msg:
            formatted_result = warning_msg + formatted_result
        
        return formatted_result
        
    except Exception as e:
        error_msg = f"❌ Error analyzing multiple tickers: {str(e)}\n\n"
        error_msg += "Possible causes:\n"
        error_msg += "- Invalid ticker symbols in the list\n"
        error_msg += "- Network connectivity issues\n"
        error_msg += "- Data sources temporarily unavailable\n\n"
        error_msg += "Suggestions:\n"
        error_msg += "- Verify all ticker symbols are correct\n"
        error_msg += "- Try with fewer tickers (max 10 recommended)\n"
        error_msg += "- Try again in a few moments\n"
        error_msg += "- Use get_ticker_complete_analysis for individual tickers as fallback\n"
        
        return error_msg

@server.tool
async def analyze_sector_companies(
    sector_query: str,
    max_companies: int = 5,
    lookback_days: int = 30
) -> str:
    """
    🎯 META-TOOL (GUIDANCE): Provides instructions for sector/thematic analysis workflow.
    
    This tool does NOT execute the analysis directly. Instead, it returns clear instructions
    for the agent to follow a 2-step workflow that efficiently analyzes companies in a sector
    or theme using web search + consolidated meta-tools.
    
    This approach is designed for LLM agents with iteration budgets, ensuring efficient
    data gathering without consuming excessive iterations.
    
    :param sector_query: The sector or theme to analyze (e.g., "AI stocks", "renewable energy", "semiconductor")
    :param max_companies: Maximum number of companies to analyze (default: 5, max: 10)
    :param lookback_days: Number of days for historical data (default: 30)
    
    :return: Step-by-step instructions for the agent to execute the sector analysis workflow
    
    Example Usage:
        # Get instructions for AI sector analysis
        instructions = await analyze_sector_companies("AI stocks", max_companies=5)
        
        # Get instructions for renewable energy sector
        instructions = await analyze_sector_companies("renewable energy companies", max_companies=3)
        
        # Get instructions for semiconductor sector with shorter lookback
        instructions = await analyze_sector_companies("semiconductor stocks", max_companies=5, lookback_days=7)
    
    Workflow Overview:
        Step 1: Use web_search to find relevant ticker symbols
        Step 2: Use get_multi_ticker_analysis with the found tickers
        
    This 2-step approach replaces what would otherwise be 30+ individual tool calls
    with just 2 calls, dramatically reducing iteration consumption.
    """
    
    # Limit max_companies to reasonable bounds
    max_companies = min(max(1, max_companies), 20)
    
    # Generate the guidance message
    guidance = f"""
🎯 SECTOR ANALYSIS WORKFLOW: {sector_query}
{'=' * 70}

To efficiently analyze companies in this sector/theme, follow this 2-step workflow:

STEP 1: FIND TICKER SYMBOLS
----------------------------
Use your web_search tool to find relevant ticker symbols:

Recommended search query:
  "top {sector_query} 2025 ticker symbols"
  
Alternative queries if needed:
  - "{sector_query} stock ticker symbols list"
  - "best {sector_query} companies NYSE NASDAQ tickers"
  - "leading {sector_query} stocks ticker list"

What to extract from search results:
  ✅ Look for ticker symbols (1-5 uppercase letters)
  ✅ Verify they are US-listed stocks (NYSE, NASDAQ)
  ✅ Prioritize companies with clear relevance to "{sector_query}"
  ✅ Extract up to {max_companies} ticker symbols

Expected format: AAPL, MSFT, GOOGL (comma-separated, uppercase)


STEP 2: ANALYZE ALL TICKERS IN ONE CALL
----------------------------------------
Once you have the ticker symbols, use the meta-tool:

  get_multi_ticker_analysis(
    tickers="TICKER1,TICKER2,TICKER3,...",
    lookback_days={lookback_days}
  )

This single call will retrieve ALL financial data for ALL tickers in parallel:
  • Company information (sector, industry, market cap)
  • Price performance ({lookback_days}-day trends)
  • Recent news headlines
  • SEC filings
  • Earnings data
  • Short volume metrics
  • Google Trends analysis


EXAMPLE WORKFLOW FOR "{sector_query}":
{'=' * 70}

1️⃣ Execute web_search:
   Query: "top {sector_query} 2025 ticker symbols"
   
   Expected result: Find articles listing relevant companies
   Extract tickers: e.g., "NVDA, AMD, INTC, AVGO, QCOM"

2️⃣ Execute get_multi_ticker_analysis:
   Call: get_multi_ticker_analysis("NVDA,AMD,INTC,AVGO,QCOM", lookback_days={lookback_days})
   
   Result: Complete financial analysis for all 5 companies in ~1 iteration
   
3️⃣ Generate your report:
   Use the consolidated data to create your sector analysis


EFFICIENCY COMPARISON:
{'=' * 70}

❌ WRONG APPROACH (30+ iterations):
   - web_search for each company individually
   - get_info for each ticker
   - get_news for each ticker
   - get_sec_filings for each ticker
   - get_earnings for each ticker
   - ... (7+ calls per ticker × {max_companies} tickers = 35+ calls)

✅ CORRECT APPROACH (2-3 iterations):
   - 1 web_search call to find all tickers
   - 1 get_multi_ticker_analysis call for all data
   - Generate report with consolidated data


IMPORTANT NOTES:
{'=' * 70}

• If web_search doesn't find clear ticker symbols:
  - Try alternative search queries (see suggestions above)
  - Look for financial news sites, stock screeners, or sector ETF holdings
  - As fallback, you can use well-known tickers for the sector

• If you find more than {max_companies} tickers:
  - Prioritize by market cap, relevance, or recent news
  - You can make multiple calls to get_multi_ticker_analysis if needed
  - Maximum 10 tickers per call for optimal performance

• Ticker format requirements:
  - Must be uppercase (AAPL, not aapl)
  - US-listed stocks only (NYSE, NASDAQ)
  - Comma-separated with no spaces: "AAPL,MSFT,GOOGL"

• For lookback_days parameter:
  - 7 days: Quick snapshot, minimal tokens
  - 30 days: Standard analysis (recommended)
  - 90 days: Comprehensive long-term view


NOW PROCEED WITH STEP 1: Execute web_search to find ticker symbols for "{sector_query}"
"""
    
    return guidance.strip()

# --- CONFIGURATION TOOLS (MCP Configuration Management) ---

@server.tool
async def configure_api_key(provider: str, api_key: str) -> str:
    """
    Configure an API key for a specific provider.
    
    This tool allows you to set API keys for optional data sources directly through MCP,
    without needing to edit configuration files manually. The configuration is persisted
    to the YAML config file for future sessions.
    
    Supported providers:
    - alpha_vantage: Alpha Vantage API for additional earnings data
    - serpapi: SerpAPI for Google Trends fallback
    
    :param provider: Provider name (alpha_vantage, serpapi)
    :param api_key: API key to configure
    :return: Confirmation message with validation status
    
    Example Usage:
        # Configure Alpha Vantage API key
        result = await configure_api_key("alpha_vantage", "YOUR_KEY_HERE")
        
        # Configure SerpAPI key
        result = await configure_api_key("serpapi", "YOUR_SERPAPI_KEY")
    
    Note:
        - The API key will be validated before being saved
        - Invalid keys will still be saved but a warning will be shown
        - Keys are persisted to ~/.iso_financial_mcp/config/datasources.yaml
    """
    # Validate provider
    valid_providers = ["alpha_vantage", "serpapi"]
    if provider not in valid_providers:
        return f"❌ Invalid provider '{provider}'. Valid providers: {', '.join(valid_providers)}"
    
    # Store in configuration manager
    config_key = f"{provider}.api_key"
    config_manager.set_mcp_config(config_key, api_key)
    
    # Also enable the provider
    config_manager.set_mcp_config(f"{provider}.enabled", True)
    
    # Validate the key by testing it
    try:
        is_valid, message = await config_manager.validate_api_key(provider, api_key)
        
        if is_valid:
            return f"✅ API key for {provider} configured and validated successfully!\n\n" \
                   f"The key has been saved to your configuration file and will be used in future sessions.\n" \
                   f"You can now use data sources that require {provider}."
        else:
            return f"⚠️ API key for {provider} has been configured but validation failed.\n\n" \
                   f"Validation message: {message}\n\n" \
                   f"The key has been saved, but please verify it's correct. Common issues:\n" \
                   f"- Invalid or expired API key\n" \
                   f"- API rate limit exceeded (try again later)\n" \
                   f"- Network connectivity issues\n\n" \
                   f"You can test the key again by reconfiguring it or checking data source status."
    except Exception as e:
        return f"⚠️ API key for {provider} has been configured but validation encountered an error.\n\n" \
               f"Error: {str(e)}\n\n" \
               f"The key has been saved and may still work. Try using it with data retrieval tools."

@server.tool
async def get_configuration() -> str:
    """
    Get current configuration (API keys are masked for security).
    
    This tool shows the current configuration including API keys (masked), cache settings,
    and other configuration options. It helps you verify what's configured and identify
    what might need to be set up.
    
    :return: Current configuration as formatted string
    
    Example Usage:
        # View current configuration
        result = await get_configuration()
    
    Note:
        - API keys are masked (only last 4 characters shown)
        - Configuration is merged from all sources (MCP, env vars, YAML, defaults)
        - Priority order: MCP tools > env vars > YAML > defaults
    """
    try:
        config = config_manager.get_all_config(mask_secrets=True)
        
        output = ["📋 Current Configuration", "=" * 70, ""]
        
        # API Keys section
        output.append("🔑 API Keys:")
        output.append("")
        
        for provider in ["alpha_vantage", "serpapi"]:
            provider_config = config.get(provider, {})
            enabled = provider_config.get("enabled", False)
            api_key = provider_config.get("api_key")
            
            if api_key:
                # Show masked key
                if isinstance(api_key, str) and api_key.startswith("..."):
                    masked = api_key
                elif isinstance(api_key, str) and len(api_key) > 4:
                    masked = f"...{api_key[-4:]}"
                else:
                    masked = "****"
                
                status = "✅ Configured" if enabled else "⚠️ Configured but disabled"
                output.append(f"  • {provider.replace('_', ' ').title()}: {masked} {status}")
            else:
                output.append(f"  • {provider.replace('_', ' ').title()}: ❌ Not configured")
        
        output.append("")
        
        # Cache configuration
        cache_config = config.get("cache", {})
        if cache_config:
            output.append("💾 Cache Configuration:")
            output.append("")
            
            memory_cache = cache_config.get("memory", {})
            if memory_cache:
                output.append(f"  Memory Cache:")
                output.append(f"    • TTL: {memory_cache.get('ttl_seconds', 'N/A')} seconds")
                output.append(f"    • Max Size: {memory_cache.get('max_size', 'N/A')} entries")
            
            disk_cache = cache_config.get("disk", {})
            if disk_cache:
                output.append(f"  Disk Cache:")
                output.append(f"    • Enabled: {'Yes' if disk_cache.get('enabled', False) else 'No'}")
                output.append(f"    • TTL: {disk_cache.get('ttl_seconds', 'N/A')} seconds")
                output.append(f"    • Max Size: {disk_cache.get('max_size_mb', 'N/A')} MB")
                output.append(f"    • Path: {disk_cache.get('path', 'N/A')}")
            
            output.append("")
        
        # Configuration sources info
        output.append("ℹ️  Configuration Priority:")
        output.append("  1. MCP tools (runtime configuration) - highest priority")
        output.append("  2. Environment variables")
        output.append("  3. YAML file (~/.iso_financial_mcp/config/datasources.yaml)")
        output.append("  4. Default values - lowest priority")
        output.append("")
        
        # Help text
        output.append("💡 Tips:")
        output.append("  • Use configure_api_key() to set API keys")
        output.append("  • Use list_data_sources() to see available data sources")
        output.append("  • API keys are persisted to YAML config for future sessions")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ Error retrieving configuration: {str(e)}\n\n" \
               f"This is unexpected. Please check the logs for more details."

@server.tool
async def list_data_sources() -> str:
    """
    List all available data sources with their status.
    
    This tool shows all data sources available in IsoFinancial-MCP, indicating which ones
    are enabled, which require API keys, and which are ready to use.
    
    :return: List of data sources with status (enabled/disabled, requires_key)
    
    Example Usage:
        # List all data sources
        result = await list_data_sources()
    
    Note:
        - Free sources (no API key required) are always available
        - Optional sources require API key configuration
        - Use configure_api_key() to enable optional sources
    """
    try:
        # Check which API keys are configured
        alpha_vantage_key = config_manager.get("alpha_vantage.api_key")
        serpapi_key = config_manager.get("serpapi.api_key")
        
        sources = [
            {
                "name": "Yahoo Finance",
                "enabled": True,
                "requires_key": False,
                "description": "Market data, prices, options, financials, holders",
                "endpoints": "get_info, get_historical_prices, get_options, get_financials, etc."
            },
            {
                "name": "SEC EDGAR",
                "enabled": True,
                "requires_key": False,
                "description": "SEC filings (8-K, 10-Q, 10-K, S-3, 424B, etc.)",
                "endpoints": "get_sec_filings"
            },
            {
                "name": "FINRA",
                "enabled": True,
                "requires_key": False,
                "description": "Daily short volume data with ratios and trends",
                "endpoints": "get_finra_short_volume"
            },
            {
                "name": "Google Trends (pytrends)",
                "enabled": True,
                "requires_key": False,
                "description": "Search volume trends and momentum analysis",
                "endpoints": "get_google_trends"
            },
            {
                "name": "News (RSS Feeds)",
                "enabled": True,
                "requires_key": False,
                "description": "Recent news headlines from multiple sources",
                "endpoints": "get_news_headlines"
            },
            {
                "name": "Earnings Calendar",
                "enabled": True,
                "requires_key": False,
                "description": "Earnings dates, EPS estimates and actuals",
                "endpoints": "get_earnings_calendar"
            },
            {
                "name": "Alpha Vantage",
                "enabled": alpha_vantage_key is not None,
                "requires_key": True,
                "description": "Additional earnings data and fundamentals",
                "endpoints": "Used as fallback in earnings_source",
                "signup_url": "https://www.alphavantage.co/support/#api-key"
            },
            {
                "name": "SerpAPI",
                "enabled": serpapi_key is not None,
                "requires_key": True,
                "description": "Google Trends fallback (when pytrends fails)",
                "endpoints": "Used as fallback in trends_source",
                "signup_url": "https://serpapi.com/users/sign_up"
            }
        ]
        
        output = ["📊 Available Data Sources", "=" * 70, ""]
        
        # Free sources
        output.append("✅ FREE SOURCES (No API Key Required):")
        output.append("")
        
        for source in sources:
            if not source["requires_key"]:
                status = "✅" if source["enabled"] else "❌"
                output.append(f"{status} {source['name']}")
                output.append(f"   {source['description']}")
                output.append(f"   Endpoints: {source['endpoints']}")
                output.append("")
        
        # Optional sources
        output.append("🔑 OPTIONAL SOURCES (API Key Required):")
        output.append("")
        
        for source in sources:
            if source["requires_key"]:
                if source["enabled"]:
                    status = "✅ Configured"
                else:
                    status = "⚠️ Not configured"
                
                output.append(f"{status} {source['name']}")
                output.append(f"   {source['description']}")
                output.append(f"   Usage: {source['endpoints']}")
                
                if not source["enabled"] and "signup_url" in source:
                    output.append(f"   Sign up: {source['signup_url']}")
                    output.append(f"   Configure: configure_api_key('{source['name'].lower().replace(' ', '_')}', 'YOUR_KEY')")
                
                output.append("")
        
        # Meta-tools info
        output.append("🎯 META-TOOLS (Consolidated Data Retrieval):")
        output.append("")
        output.append("  • get_ticker_complete_analysis(ticker)")
        output.append("    Fetches ALL data for a single ticker in one call")
        output.append("    Replaces 7+ individual tool calls")
        output.append("")
        output.append("  • get_multi_ticker_analysis(tickers)")
        output.append("    Analyzes multiple tickers in parallel")
        output.append("    Replaces 7+ calls per ticker")
        output.append("")
        output.append("  • analyze_sector_companies(sector_query)")
        output.append("    Provides workflow guidance for sector analysis")
        output.append("")
        
        # Help text
        output.append("💡 Tips:")
        output.append("  • All free sources are ready to use immediately")
        output.append("  • Optional sources enhance data coverage but aren't required")
        output.append("  • Use configure_api_key() to enable optional sources")
        output.append("  • Use get_configuration() to view current settings")
        output.append("  • Prefer meta-tools for efficient multi-source data retrieval")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ Error listing data sources: {str(e)}\n\n" \
               f"This is unexpected. Please check the logs for more details."

# --- HEALTH CHECK TOOLS (MCP Health Monitoring) ---

@server.tool
async def get_health_status() -> str:
    """
    Get health status of all data sources.
    
    This tool provides a comprehensive health report for all data sources, including
    success rates, latency metrics, recent errors, and overall status. Use this to
    diagnose issues or verify that data sources are functioning properly.
    
    :return: Health status report for all sources with metrics and status indicators
    
    Example Usage:
        # Check health of all data sources
        result = await get_health_status()
    
    Status Indicators:
        ✅ Healthy: Success rate >= 70%
        ⚠️ Degraded: Success rate 30-70%
        ❌ Unhealthy: Success rate < 30%
        ❓ Unknown: No recent requests
    
    Metrics Included:
        - Success rate (percentage of successful requests)
        - Average latency (response time in milliseconds)
        - Total requests (number of requests tracked)
        - Last success (timestamp of last successful request)
        - Recent errors (list of recent error types)
    
    Note:
        Health metrics are tracked over a rolling window of recent requests.
        Use test_data_source() to actively test a specific source.
    """
    try:
        # Get or create health monitor from data manager
        from .reliability.health_monitor import HealthMonitor
        from .reliability.data_manager import DataManager
        
        # Use the global data manager instance
        data_manager = DataManager()
        health_monitor = data_manager.health_monitor
        
        # Get health status for all sources
        all_status = health_monitor.get_all_health_status()
        
        if not all_status:
            return "📊 No health data available yet.\n\n" \
                   "Health metrics are collected as data sources are used.\n" \
                   "Try fetching some data first, then check health status again.\n\n" \
                   "You can also use test_data_source() to actively test a source."
        
        output = ["🏥 Data Sources Health Status", "=" * 70, ""]
        
        # Sort sources by status (unhealthy first, then degraded, then healthy)
        status_priority = {"unhealthy": 0, "degraded": 1, "healthy": 2, "unknown": 3}
        sorted_sources = sorted(
            all_status.items(),
            key=lambda x: (status_priority.get(x[1].status, 4), x[0])
        )
        
        for source_name, status in sorted_sources:
            # Status emoji
            if status.status == "healthy":
                emoji = "✅"
            elif status.status == "degraded":
                emoji = "⚠️"
            elif status.status == "unhealthy":
                emoji = "❌"
            else:
                emoji = "❓"
            
            output.append(f"{emoji} {source_name.upper()}")
            output.append(f"   Status: {status.status.title()}")
            output.append(f"   Success Rate: {status.success_rate * 100:.1f}%")
            output.append(f"   Avg Latency: {status.avg_latency_ms}ms")
            output.append(f"   Total Requests: {status.total_requests}")
            
            if status.last_success:
                # Calculate time since last success
                time_since = datetime.now() - status.last_success
                if time_since.total_seconds() < 60:
                    time_str = f"{int(time_since.total_seconds())}s ago"
                elif time_since.total_seconds() < 3600:
                    time_str = f"{int(time_since.total_seconds() / 60)}m ago"
                elif time_since.total_seconds() < 86400:
                    time_str = f"{int(time_since.total_seconds() / 3600)}h ago"
                else:
                    time_str = f"{int(time_since.total_seconds() / 86400)}d ago"
                
                output.append(f"   Last Success: {time_str}")
            else:
                output.append(f"   Last Success: Never")
            
            if status.recent_errors:
                # Show up to 3 most recent errors
                errors_display = status.recent_errors[:3]
                output.append(f"   Recent Errors: {', '.join(errors_display)}")
            
            output.append("")
        
        # Add summary
        healthy_count = sum(1 for _, s in all_status.items() if s.status == "healthy")
        degraded_count = sum(1 for _, s in all_status.items() if s.status == "degraded")
        unhealthy_count = sum(1 for _, s in all_status.items() if s.status == "unhealthy")
        unknown_count = sum(1 for _, s in all_status.items() if s.status == "unknown")
        
        output.append("📈 SUMMARY")
        output.append(f"   Total Sources: {len(all_status)}")
        output.append(f"   ✅ Healthy: {healthy_count}")
        output.append(f"   ⚠️ Degraded: {degraded_count}")
        output.append(f"   ❌ Unhealthy: {unhealthy_count}")
        output.append(f"   ❓ Unknown: {unknown_count}")
        output.append("")
        
        # Add tips
        output.append("💡 TIPS")
        output.append("   • Use test_data_source() to actively test a specific source")
        output.append("   • Degraded sources may still work but with reduced reliability")
        output.append("   • Unhealthy sources will trigger automatic fallback to alternatives")
        output.append("   • Health metrics are tracked over a rolling window of recent requests")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ Error retrieving health status: {str(e)}\n\n" \
               f"This is unexpected. Please check the logs for more details."

@server.tool
async def test_data_source(source_name: str, ticker: str = "AAPL") -> str:
    """
    Test a specific data source with a sample request.
    
    This tool actively tests a data source by making a real request and measuring
    the response time and success. Use this to diagnose issues with specific sources
    or verify that a source is working correctly.
    
    :param source_name: Name of the source to test (sec, trends, earnings, finra, news, yfinance)
    :param ticker: Ticker symbol to test with (default: AAPL)
    :return: Test result with timing, success status, error details, and data preview
    
    Example Usage:
        # Test SEC filings source
        result = await test_data_source("sec", "AAPL")
        
        # Test Google Trends source
        result = await test_data_source("trends", "NVDA")
        
        # Test earnings calendar
        result = await test_data_source("earnings", "MSFT")
    
    Supported Sources:
        - sec: SEC EDGAR filings
        - trends: Google Trends search volume
        - earnings: Earnings calendar
        - finra: FINRA short volume
        - news: News headlines
        - yfinance: Yahoo Finance data
    
    Note:
        This tool makes a real request to the data source, so it will consume
        API rate limits and may take a few seconds to complete.
    """
    import time
    
    # Normalize source name
    source_name = source_name.lower().strip()
    ticker = ticker.upper().strip()
    
    # Validate source name
    valid_sources = ["sec", "trends", "earnings", "finra", "news", "yfinance"]
    if source_name not in valid_sources:
        return f"❌ Invalid source name: {source_name}\n\n" \
               f"Valid sources: {', '.join(valid_sources)}\n\n" \
               f"Example: test_data_source('sec', 'AAPL')"
    
    output = [f"🧪 Testing {source_name.upper()} with ticker {ticker}...", ""]
    
    start_time = time.time()
    
    try:
        # Route to appropriate source
        if source_name == "sec":
            result = await sec_source.get_sec_filings(ticker, ["8-K"], 30)
            preview = f"Found {len(result)} filings" if result else "No filings found"
            if result and len(result) > 0:
                preview += f"\nMost recent: {result[0].get('form', 'N/A')} on {result[0].get('date', 'N/A')}"
        
        elif source_name == "trends":
            result = await trends_source.get_google_trends(ticker, 30)
            if result.get("error"):
                raise Exception(result["error"])
            preview = f"Latest search volume: {result.get('latest', 0)}"
            preview += f"\nTrend: {result.get('trend', 'unknown').replace('_', ' ').title()}"
        
        elif source_name == "earnings":
            result = await earnings_source.get_earnings_calendar(ticker)
            preview = f"Found {len(result)} earnings records" if result else "No earnings data found"
            if result and len(result) > 0:
                upcoming = [e for e in result if e.get('date', '') >= datetime.now().strftime('%Y-%m-%d')]
                preview += f"\nUpcoming earnings: {len(upcoming)}"
        
        elif source_name == "finra":
            result = await finra_source.get_finra_short_volume(ticker, None, None)
            preview = f"Found {len(result)} days of short volume data" if result else "No short volume data found"
            if result and len(result) > 0:
                latest = result[0]
                preview += f"\nLatest short ratio: {latest.get('short_ratio', 0):.2%}"
        
        elif source_name == "news":
            result = await news_source.get_news_headlines(ticker, 5, 3)
            preview = f"Found {len(result)} news articles" if result else "No news found"
            if result and len(result) > 0:
                preview += f"\nMost recent: {result[0].get('title', 'N/A')[:60]}..."
        
        elif source_name == "yfinance":
            result = await yfinance_source.get_info(ticker)
            preview = f"Company: {result.get('longName', 'N/A')}" if result else "No info found"
            if result:
                preview += f"\nSector: {result.get('sector', 'N/A')}"
                preview += f"\nMarket Cap: ${result.get('marketCap', 0):,.0f}" if result.get('marketCap') else ""
        
        else:
            return f"❌ Source '{source_name}' not implemented yet."
        
        elapsed = time.time() - start_time
        
        output.append(f"✅ Test successful!")
        output.append(f"⏱️  Response time: {elapsed:.2f}s")
        output.append("")
        output.append(f"📊 Data preview:")
        output.append(preview)
        output.append("")
        
        # Add interpretation
        output.append("💡 Interpretation:")
        if elapsed < 1.0:
            output.append("   • Excellent response time (< 1s)")
        elif elapsed < 3.0:
            output.append("   • Good response time (1-3s)")
        elif elapsed < 5.0:
            output.append("   • Acceptable response time (3-5s)")
        else:
            output.append("   • Slow response time (> 5s) - may indicate issues")
        
        if result:
            output.append("   • Data source is functioning correctly")
        else:
            output.append("   • No data returned - may be normal for this ticker/timeframe")
        
    except Exception as e:
        elapsed = time.time() - start_time
        output.append(f"❌ Test failed!")
        output.append(f"⏱️  Time to failure: {elapsed:.2f}s")
        output.append("")
        output.append(f"🔴 Error: {str(e)}")
        output.append("")
        
        # Add troubleshooting tips
        output.append("🔧 Troubleshooting:")
        output.append("   • Verify the ticker symbol is correct")
        output.append("   • Check if the data source requires an API key")
        output.append("   • Try again in a few moments (may be rate limited)")
        output.append("   • Check network connectivity")
        output.append("   • Use get_health_status() to see overall source health")
    
    return "\n".join(output)

# --- LEGACY TOOLS (Individual Data Sources) ---
# Note: These tools are maintained for backward compatibility.
# For new implementations, prefer the meta-tools above for better performance.

# Use the instance decorator @server.tool
@server.tool
async def get_info(ticker: str) -> str:
    """
    Get general information about a ticker (e.g., company profile, sector, summary).
    :param ticker: The stock ticker symbol (e.g., 'AAPL').
    """
    info = await yf_source.get_info(ticker)
    if not info:
        return f"Could not retrieve information for {ticker}."
    return '\n'.join([f"{key}: {value}" for key, value in info.items()])

@server.tool
async def get_historical_prices(ticker: str, period: str = "1y", interval: str = "1d") -> str:
    """
    Get historical market data for a ticker.
    :param ticker: The stock ticker symbol.
    :param period: The time period (e.g., '1y', '6mo'). Default is '1y'.
    :param interval: The data interval (e.g., '1d', '1wk'). Default is '1d'.
    """
    df = await yf_source.get_historical_prices(ticker, period, interval)
    return dataframe_to_string(df)

@server.tool
async def get_actions(ticker: str) -> str:
    """
    Get corporate actions (dividends and stock splits).
    :param ticker: The stock ticker symbol.
    """
    df = await yf_source.get_actions(ticker)
    return dataframe_to_string(df)

@server.tool
async def get_balance_sheet(ticker: str, freq: str = "yearly") -> str:
    """
    Get balance sheet data.
    :param ticker: The stock ticker symbol.
    :param freq: Frequency, 'yearly' or 'quarterly'. Default is 'yearly'.
    """
    df = await yf_source.get_balance_sheet(ticker, freq)
    return dataframe_to_string(df)

@server.tool
async def get_financials(ticker: str, freq: str = "yearly") -> str:
    """
    Get financial statements.
    :param ticker: The stock ticker symbol.
    :param freq: Frequency, 'yearly' or 'quarterly'. Default is 'yearly'.
    """
    df = await yf_source.get_financials(ticker, freq)
    return dataframe_to_string(df)

@server.tool
async def get_cash_flow(ticker: str, freq: str = "yearly") -> str:
    """
    Get cash flow statements.
    :param ticker: The stock ticker symbol.
    :param freq: Frequency, 'yearly' or 'quarterly'. Default is 'yearly'.
    """
    df = await yf_source.get_cash_flow(ticker, freq)
    return dataframe_to_string(df)

@server.tool
async def get_major_holders(ticker: str) -> str:
    """
    Get major shareholders.
    :param ticker: The stock ticker symbol.
    """
    df = await yf_source.get_major_holders(ticker)
    return dataframe_to_string(df)

@server.tool
async def get_institutional_holders(ticker: str) -> str:
    """
    Get institutional investors.
    :param ticker: The stock ticker symbol.
    """
    df = await yf_source.get_institutional_holders(ticker)
    return dataframe_to_string(df)

@server.tool
async def get_recommendations(ticker: str) -> str:
    """
    Get analyst recommendations.
    :param ticker: The stock ticker symbol.
    """
    df = await yf_source.get_recommendations(ticker)
    return dataframe_to_string(df)

@server.tool
async def get_earnings_dates(ticker: str) -> str:
    """
    Get upcoming and historical earnings dates.
    :param ticker: The stock ticker symbol.
    """
    df = await yf_source.get_earnings_dates(ticker)
    return dataframe_to_string(df)

@server.tool
async def get_isin(ticker: str) -> str:
    """
    Get the ISIN of the ticker.
    :param ticker: The stock ticker symbol.
    """
    isin = await yf_source.get_isin(ticker)
    return isin or f"ISIN not found for {ticker}."

@server.tool
async def get_options_expirations(ticker: str) -> str:
    """
    Get options expiration dates.
    :param ticker: The stock ticker symbol.
    """
    expirations = await yf_source.get_options_expirations(ticker)
    if not expirations:
        return f"No options expirations found for {ticker}."
    return ", ".join(expirations)

@server.tool
async def get_option_chain(ticker: str, expiration_date: str) -> str:
    """
    Get the option chain for a specific expiration date.
    :param ticker: The stock ticker symbol.
    :param expiration_date: The expiration date in YYYY-MM-DD format.
    """
    chain = await yf_source.get_option_chain(ticker, expiration_date)
    if chain is None:
        return f"Could not retrieve option chain for {ticker} on {expiration_date}."

    calls_str = "No calls data."
    if chain.calls is not None and not chain.calls.empty:
        calls_str = dataframe_to_string(chain.calls)

    puts_str = "No puts data."
    if chain.puts is not None and not chain.puts.empty:
        puts_str = dataframe_to_string(chain.puts)

    return f"--- CALLS for {ticker} expiring on {expiration_date} ---\n{calls_str}\n\n--- PUTS for {ticker} expiring on {expiration_date} ---\n{puts_str}"

@server.tool
async def get_sec_filings(
    ticker: str,
    form_types: str = "8-K,S-3,424B,10-Q,10-K",
    lookback_days: int = 30
) -> str:
    """
    Get SEC filings from EDGAR API with form type filtering.
    :param ticker: The stock ticker symbol.
    :param form_types: Comma-separated list of form types to filter (default: "8-K,S-3,424B,10-Q,10-K").
    :param lookback_days: Number of days to look back for filings (default: 30).
    """
    try:
        # Parse form types from comma-separated string
        form_list = [form.strip() for form in form_types.split(",")]
        
        filings = await sec_source.get_sec_filings(ticker, form_list, lookback_days)
        
        if not filings:
            return f"No SEC filings found for {ticker} in the last {lookback_days} days."
        
        # Format filings as readable text
        result = f"SEC Filings for {ticker} (Last {lookback_days} days):\n\n"
        
        for filing in filings:
            result += f"Date: {filing['date']}\n"
            result += f"Form: {filing['form']}\n"
            result += f"Title: {filing['title']}\n"
            result += f"URL: {filing['url']}\n"
            result += f"Accession: {filing['accession_number']}\n"
            result += "-" * 50 + "\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving SEC filings for {ticker}: {str(e)}"

@server.tool
async def get_finra_short_volume(
    ticker: str,
    start_date: str = "",
    end_date: str = ""
) -> str:
    """
    Get FINRA daily short volume data with ratio calculations.
    :param ticker: The stock ticker symbol.
    :param start_date: Start date in YYYY-MM-DD format (default: 30 days ago).
    :param end_date: End date in YYYY-MM-DD format (default: today).
    """
    try:
        # Use None for empty strings to trigger default behavior
        start = start_date if start_date else None
        end = end_date if end_date else None
        
        short_data = await finra_source.get_finra_short_volume(ticker, start, end)
        
        if not short_data:
            return f"No FINRA short volume data found for {ticker}."
        
        # Calculate aggregate metrics
        metrics = finra_source.calculate_short_metrics(short_data)
        
        # Format results
        result = f"FINRA Short Volume Data for {ticker}:\n\n"
        
        # Summary metrics
        result += "=== SUMMARY METRICS ===\n"
        result += f"Days Analyzed: {metrics.get('days_analyzed', 0)}\n"
        result += f"Overall Short Ratio: {metrics.get('overall_short_ratio', 0):.2%}\n"
        result += f"Average Daily Short Ratio: {metrics.get('average_daily_short_ratio', 0):.2%}\n"
        result += f"Recent Short Ratio (5-day): {metrics.get('recent_short_ratio', 0):.2%}\n"
        result += f"Trend: {metrics.get('short_ratio_trend', 'N/A').title()}\n\n"
        
        # Daily data (show last 10 days)
        result += "=== DAILY DATA (Last 10 Days) ===\n"
        for i, day_data in enumerate(short_data[:10]):
            result += f"Date: {day_data['date']}\n"
            result += f"  Short Volume: {day_data['short_volume']:,}\n"
            result += f"  Total Volume: {day_data['total_volume']:,}\n"
            result += f"  Short Ratio: {day_data['short_ratio']:.2%}\n"
            if i < len(short_data[:10]) - 1:
                result += "-" * 30 + "\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving FINRA short volume for {ticker}: {str(e)}"

@server.tool
async def get_earnings_calendar(ticker: str) -> str:
    """
    Get earnings calendar data with EPS estimates, actuals, and surprise percentages.
    :param ticker: The stock ticker symbol.
    """
    try:
        earnings_data = await earnings_source.get_earnings_calendar(ticker)
        
        if not earnings_data:
            return f"No earnings calendar data found for {ticker}."
        
        # Format results
        result = f"Earnings Calendar for {ticker}:\n\n"
        
        # Show upcoming earnings first
        upcoming = earnings_source.get_upcoming_earnings(earnings_data, days_ahead=90)
        if upcoming:
            result += "=== UPCOMING EARNINGS ===\n"
            for earning in upcoming:
                result += f"Date: {earning.get('date', 'N/A')}\n"
                result += f"Period: {earning.get('period', 'N/A')}\n"
                result += f"Timing: {earning.get('timing', 'N/A')}\n"
                if earning.get('eps_estimate'):
                    result += f"EPS Estimate: ${earning['eps_estimate']:.2f}\n"
                result += "-" * 30 + "\n"
            result += "\n"
        
        # Show historical earnings
        historical = [e for e in earnings_data if e not in upcoming][:10]  # Last 10 historical
        if historical:
            result += "=== RECENT HISTORICAL EARNINGS ===\n"
            for earning in historical:
                result += f"Date: {earning.get('date', 'N/A')}\n"
                result += f"Period: {earning.get('period', 'N/A')}\n"
                result += f"Timing: {earning.get('timing', 'N/A')}\n"
                
                if earning.get('eps_estimate') is not None:
                    result += f"EPS Estimate: ${earning['eps_estimate']:.2f}\n"
                if earning.get('eps_actual') is not None:
                    result += f"EPS Actual: ${earning['eps_actual']:.2f}\n"
                if earning.get('eps_surprise') is not None:
                    result += f"EPS Surprise: ${earning['eps_surprise']:.2f}\n"
                if earning.get('surprise_percentage') is not None:
                    result += f"Surprise %: {earning['surprise_percentage']:.1f}%\n"
                
                result += "-" * 30 + "\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving earnings calendar for {ticker}: {str(e)}"

@server.tool
async def get_news_headlines(
    ticker: str,
    limit: int = 10,
    lookback_days: int = 3
) -> str:
    """
    Get recent news headlines with source attribution and duplicate detection.
    :param ticker: The stock ticker symbol.
    :param limit: Maximum number of headlines to return (default: 10).
    :param lookback_days: Number of days to look back for news (default: 3).
    """
    try:
        news_data = await news_source.get_news_headlines(ticker, limit, lookback_days)
        
        if not news_data:
            return f"No recent news headlines found for {ticker} in the last {lookback_days} days."
        
        # Format results
        result = f"Recent News Headlines for {ticker} (Last {lookback_days} days):\n\n"
        
        for i, article in enumerate(news_data, 1):
            result += f"{i}. {article.get('title', 'No title')}\n"
            result += f"   Source: {article.get('source', 'Unknown')}\n"
            result += f"   Published: {article.get('published_at', 'Unknown date')}\n"
            result += f"   URL: {article.get('url', 'No URL')}\n"
            
            if article.get('summary'):
                # Truncate summary to keep response manageable
                summary = article['summary'][:200] + "..." if len(article['summary']) > 200 else article['summary']
                result += f"   Summary: {summary}\n"
            
            result += "-" * 60 + "\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving news headlines for {ticker}: {str(e)}"

@server.tool
async def get_google_trends(
    term: str,
    window_days: int = 30
) -> str:
    """
    Get Google Trends search volume data with trend analysis.
    :param term: Search term (typically ticker symbol or company name).
    :param window_days: Time window in days for trend analysis (default: 30).
    """
    try:
        trends_data = await trends_source.get_google_trends(term, window_days)
        
        if trends_data.get("error"):
            return f"Error retrieving Google Trends for '{term}': {trends_data['error']}"
        
        if not trends_data.get("series"):
            return f"No Google Trends data found for '{term}' in the last {window_days} days."
        
        # Format results
        result = f"Google Trends Data for '{term}' (Last {window_days} days):\n\n"
        
        # Summary metrics
        result += "=== SUMMARY METRICS ===\n"
        result += f"Latest Search Volume: {trends_data.get('latest', 0)}\n"
        result += f"Average Search Volume: {trends_data.get('average', 0)}\n"
        result += f"Peak Search Volume: {trends_data.get('peak_value', 0)}\n"
        result += f"Peak Date: {trends_data.get('peak_date', 'N/A')}\n"
        result += f"Trend Direction: {trends_data.get('trend', 'unknown').replace('_', ' ').title()}\n"
        result += f"Data Points: {trends_data.get('total_points', 0)}\n\n"
        
        # Momentum analysis
        momentum_data = trends_source.analyze_trend_momentum(trends_data.get("series", []))
        result += "=== MOMENTUM ANALYSIS ===\n"
        result += f"Momentum: {momentum_data.get('momentum', 'unknown').replace('_', ' ').title()}\n"
        result += f"Momentum Score: {momentum_data.get('score', 0)}\n"
        result += f"Recent Average: {momentum_data.get('recent_average', 0)}\n"
        result += f"Historical Average: {momentum_data.get('historical_average', 0)}\n\n"
        
        # Related queries
        related = trends_data.get("related_queries", {})
        if related.get("top") or related.get("rising"):
            result += "=== RELATED QUERIES ===\n"
            
            if related.get("top"):
                result += "Top Related:\n"
                for i, query in enumerate(related["top"][:5], 1):
                    result += f"  {i}. {query}\n"
                result += "\n"
            
            if related.get("rising"):
                result += "Rising Related:\n"
                for i, query in enumerate(related["rising"][:5], 1):
                    result += f"  {i}. {query}\n"
                result += "\n"
        
        # Recent data points (last 10)
        series = trends_data.get("series", [])
        if len(series) > 0:
            result += "=== RECENT DATA POINTS (Last 10) ===\n"
            for point in series[-10:]:
                result += f"Date: {point.get('date', 'N/A')} - Volume: {point.get('value', 0)}\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving Google Trends for '{term}': {str(e)}"

# No need to manually create a list of tools.
# The server object is now ready and has the tools registered via the decorator.

if __name__ == "__main__":
    from . import __version__
    
    # Display welcome message
    print("=" * 70)
    print(f"🚀 IsoFinancial-MCP Server v{__version__}")
    print("=" * 70)
    print("")
    print("📊 AVAILABLE DATA SOURCES:")
    print("  ✅ Yahoo Finance - Market data, prices, options, financials")
    print("  ✅ SEC EDGAR - SEC filings (8-K, 10-Q, 10-K, S-3, 424B)")
    print("  ✅ FINRA - Daily short volume data with ratios")
    print("  ✅ Google Trends - Search volume analysis")
    print("  ✅ News (RSS) - Recent headlines from multiple sources")
    print("  ✅ Earnings Calendar - EPS estimates and actuals")
    print("")
    print("🎯 META-TOOLS: get_ticker_complete_analysis(), get_multi_ticker_analysis()")
    print("⚙️  CONFIGURATION: configure_api_key(), list_data_sources(), get_health_status()")
    print("")
    print("📖 Documentation: https://github.com/Niels-8/isofinancial-mcp")
    print("=" * 70)
    print("")
    print("📡 Server ready for MCP connections...")
    print("")
    
    server.run() 