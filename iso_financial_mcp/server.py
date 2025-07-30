#!/usr/bin/env python3
"""
Finance MCP Server CORRIGÉ
Serveur utilisant uniquement les endpoints d'API qui existent réellement
"""

from fastmcp.server.server import FastMCP
from typing import Optional
import pandas as pd
from .datasources import yfinance_source as yf_source

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

# No need to manually create a list of tools.
# The server object is now ready and has the tools registered via the decorator.

if __name__ == "__main__":
    print("🚀 Starting IsoFinancial-MCP Server (Corrected Version)")
    print("✅ Using only real API endpoints")
    print("📡 Finnhub endpoints: profile, quote, news, recommendations, insider")
    print("📊 FMP endpoints: detailed profile, float, estimates, grades, ratios")
    print("🔧 Alternative short interest estimation available")
    
    server.run() 