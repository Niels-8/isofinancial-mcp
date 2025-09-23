"""
Yahoo Finance client using yfinance
Handles pricing, volume, options data, and company fundamentals
"""

import yfinance as yf
from typing import Optional, Dict, Any, List, Tuple
from functools import lru_cache
import asyncio
import pandas as pd
import warnings
from .validation import (
    validate_ticker, validate_period_string, validate_interval_string, 
    validate_frequency, ValidationError
)

# Suppress pandas FutureWarnings from yfinance
warnings.filterwarnings('ignore', category=FutureWarning, module='yfinance')
warnings.filterwarnings('ignore', category=FutureWarning, message='.*pandas.*')
warnings.filterwarnings('ignore', category=FutureWarning, message='.*count.*positional.*')

# --- Helper Functions ---

@lru_cache(maxsize=128)
def get_ticker_obj(ticker: str) -> yf.Ticker:
    """
    Get a yfinance.Ticker object for a given ticker symbol.
    Uses caching to avoid redundant initializations.
    """
    return yf.Ticker(ticker)

async def run_in_executor(func, *args):
    """
    Run a blocking function in a separate thread to avoid blocking the asyncio event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)

# --- Core Data Fetching Functions ---

async def get_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get general information about a ticker.
    This is a core function that retrieves a wide range of data.
    """
    try:
        # Validate input
        ticker = validate_ticker(ticker)
        
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        info = await run_in_executor(lambda: ticker_obj.info)
        return info
    except ValidationError as e:
        print(f"Validation error for ticker {ticker}: {e}")
        return None
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return None

async def get_historical_prices(
    ticker: str,
    period: str = "1y",
    interval: str = "1d"
) -> Optional[pd.DataFrame]:
    """
    Get historical market data.
    """
    try:
        # Validate inputs
        ticker = validate_ticker(ticker)
        period = validate_period_string(period)
        interval = validate_interval_string(interval)
        
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        history = await run_in_executor(
            ticker_obj.history, period=period, interval=interval
        )
        return history
    except ValidationError as e:
        print(f"Validation error for {ticker}: {e}")
        return None
    except Exception as e:
        print(f"Error fetching historical prices for {ticker}: {e}")
        return None

async def get_actions(ticker: str) -> Optional[pd.DataFrame]:
    """
    Get corporate actions (dividends and stock splits).
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        actions = await run_in_executor(lambda: ticker_obj.actions)
        return actions
    except Exception as e:
        print(f"Error fetching actions for {ticker}: {e}")
        return None

async def get_balance_sheet(ticker: str, freq: str = "yearly") -> Optional[pd.DataFrame]:
    """
    Get balance sheet data. `freq` can be 'yearly' or 'quarterly'.
    """
    try:
        # Validate inputs
        ticker = validate_ticker(ticker)
        freq = validate_frequency(freq)
        
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        balance_sheet = await run_in_executor(
            lambda: ticker_obj.balance_sheet if freq == "yearly" else ticker_obj.quarterly_balance_sheet
        )
        return balance_sheet
    except ValidationError as e:
        print(f"Validation error for {ticker}: {e}")
        return None
    except Exception as e:
        print(f"Error fetching balance sheet for {ticker}: {e}")
        return None

async def get_financials(ticker: str, freq: str = "yearly") -> Optional[pd.DataFrame]:
    """
    Get financial statements. `freq` can be 'yearly' or 'quarterly'.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        financials = await run_in_executor(
            lambda: ticker_obj.financials if freq == "yearly" else ticker_obj.quarterly_financials
        )
        return financials
    except Exception as e:
        print(f"Error fetching financials for {ticker}: {e}")
        return None

async def get_cash_flow(ticker: str, freq: str = "yearly") -> Optional[pd.DataFrame]:
    """
    Get cash flow statements. `freq` can be 'yearly' or 'quarterly'.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        cash_flow = await run_in_executor(
            lambda: ticker_obj.cashflow if freq == "yearly" else ticker_obj.quarterly_cashflow
        )
        return cash_flow
    except Exception as e:
        print(f"Error fetching cash flow for {ticker}: {e}")
        return None

async def get_major_holders(ticker: str) -> Optional[pd.DataFrame]:
    """
    Get major shareholders.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        holders = await run_in_executor(lambda: ticker_obj.major_holders)
        return holders
    except Exception as e:
        print(f"Error fetching major holders for {ticker}: {e}")
        return None

async def get_institutional_holders(ticker: str) -> Optional[pd.DataFrame]:
    """
    Get institutional investors.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        holders = await run_in_executor(lambda: ticker_obj.institutional_holders)
        return holders
    except Exception as e:
        print(f"Error fetching institutional holders for {ticker}: {e}")
        return None

async def get_recommendations(ticker: str) -> Optional[pd.DataFrame]:
    """
    Get analyst recommendations.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        recos = await run_in_executor(lambda: ticker_obj.recommendations)
        return recos
    except Exception as e:
        print(f"Error fetching recommendations for {ticker}: {e}")
        return None

async def get_earnings_dates(ticker: str) -> Optional[pd.DataFrame]:
    """
    Get upcoming and historical earnings dates.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        earnings = await run_in_executor(lambda: ticker_obj.earnings_dates)
        return earnings
    except Exception as e:
        print(f"Error fetching earnings dates for {ticker}: {e}")
        return None

async def get_isin(ticker: str) -> Optional[str]:
    """
    Get the ISIN of the ticker.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        isin = await run_in_executor(lambda: ticker_obj.isin)
        return isin
    except Exception as e:
        print(f"Error fetching ISIN for {ticker}: {e}")
        return None

async def get_options_expirations(ticker: str) -> Optional[Tuple[str, ...]]:
    """
    Get options expiration dates.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        expirations = await run_in_executor(lambda: ticker_obj.options)
        return expirations
    except Exception as e:
        print(f"Error fetching options expirations for {ticker}: {e}")
        return None

async def get_option_chain(ticker: str, expiration_date: str) -> Optional[Any]:
    """
    Get the option chain for a specific expiration date.
    """
    try:
        ticker_obj = await run_in_executor(get_ticker_obj, ticker)
        chain = await run_in_executor(ticker_obj.option_chain, expiration_date)
        return chain
    except Exception as e:
        print(f"Error fetching option chain for {ticker} on {expiration_date}: {e}")
        return None 