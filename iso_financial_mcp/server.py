#!/usr/bin/env python3
"""
Finance MCP Server 
"""

from fastmcp.server.server import FastMCP
from typing import Optional, List
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

# Instantiate the server first
server = FastMCP(
    name="IsoFinancial-MCP"
)

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
    print("🚀 Starting Enhanced IsoFinancial-MCP Server")
    print("✅ Core Yahoo Finance endpoints: info, prices, options, financials, holders")
    print("🆕 NEW Enhanced endpoints for Wasaphi-Alpha-Scanner:")
    print("   📋 SEC Filings (get_sec_filings) - EDGAR API with 6h caching")
    print("   📊 FINRA Short Volume (get_finra_short_volume) - Daily short ratios with 24h caching")
    print("   📅 Earnings Calendar (get_earnings_calendar) - EPS estimates & actuals with 24h caching")
    print("   📰 News Headlines (get_news_headlines) - RSS feeds with 2h caching")
    print("   📈 Google Trends (get_google_trends) - Search volume analysis with 24h caching")
    print("🔧 All endpoints include rate limiting, error handling, and graceful degradation")
    
    server.run() 