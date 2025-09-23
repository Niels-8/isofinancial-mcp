#!/usr/bin/env python3
"""
Finance MCP Server CORRIGÉ
Serveur utilisant uniquement les endpoints d'API qui existent réellement
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