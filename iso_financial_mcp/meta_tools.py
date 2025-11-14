"""
Meta-tools module for IsoFinancial-MCP optimization.

This module provides consolidated meta-tools that retrieve all financial data
in 1-2 calls instead of 10+ individual calls, optimizing for LLM agent efficiency.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import logging

# Import datasources
from .datasources import yfinance_source
from .datasources import news_source
from .datasources import sec_source
from .datasources import earnings_source
from .datasources import finra_source
from .datasources import trends_source

# Import reliability components
from .reliability.data_manager import DataManager
from .reliability.models import DataResult

# Import source managers
from .datasources.sec_source_manager import SECSourceManager
from .datasources.trends_source_manager import TrendsSourceManager
from .datasources.earnings_source_manager import EarningsSourceManager

# Configure logging
logger = logging.getLogger(__name__)

# Initialize global instances for reuse
_data_manager = None
_sec_manager = None
_trends_manager = None
_earnings_manager = None


def _get_data_manager() -> DataManager:
    """Get or create global DataManager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager


def _get_sec_manager() -> SECSourceManager:
    """Get or create global SECSourceManager instance."""
    global _sec_manager
    if _sec_manager is None:
        _sec_manager = SECSourceManager(data_manager=_get_data_manager())
    return _sec_manager


def _get_trends_manager() -> TrendsSourceManager:
    """Get or create global TrendsSourceManager instance."""
    global _trends_manager
    if _trends_manager is None:
        _trends_manager = TrendsSourceManager()
    return _trends_manager


def _get_earnings_manager() -> EarningsSourceManager:
    """Get or create global EarningsSourceManager instance."""
    global _earnings_manager
    if _earnings_manager is None:
        _earnings_manager = EarningsSourceManager(data_manager=_get_data_manager())
    return _earnings_manager


def truncate_string(text: str, max_length: int = 500) -> str:
    """
    Truncate long text strings intelligently to save tokens.
    
    Args:
        text: The text to truncate
        max_length: Maximum length before truncation (default: 500)
    
    Returns:
        Truncated string with "[truncated]" indicator if needed
    
    Example:
        >>> truncate_string("A" * 1000, max_length=100)
        'AAAA... [truncated]'
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    
    if len(text) <= max_length:
        return text
    
    # Truncate and add indicator
    truncated = text[:max_length].rstrip()
    return f"{truncated}... [truncated]"


def format_compact_data(data: Any, max_items: int = 5) -> str:
    """
    Format data structures in a compact way to save tokens.
    
    Handles lists, dictionaries, and other data types by limiting the number
    of items displayed and providing a summary for the rest.
    
    Args:
        data: The data to format (list, dict, or other)
        max_items: Maximum number of items to display (default: 5)
    
    Returns:
        Compact string representation of the data
    
    Example:
        >>> format_compact_data(list(range(20)), max_items=5)
        '[0, 1, 2, 3, 4] +15 more items'
    """
    if data is None:
        return "None"
    
    # Handle lists
    if isinstance(data, list):
        if len(data) <= max_items:
            return str(data)
        
        displayed = data[:max_items]
        remaining = len(data) - max_items
        return f"{displayed} +{remaining} more items"
    
    # Handle dictionaries
    if isinstance(data, dict):
        if len(data) <= max_items:
            return str(data)
        
        items = list(data.items())[:max_items]
        remaining = len(data) - max_items
        displayed = {k: v for k, v in items}
        return f"{displayed} +{remaining} more items"
    
    # Handle other types
    return str(data)


async def get_financial_snapshot(
    ticker: str,
    include_options: bool = False,
    lookback_days: int = 30
) -> Dict[str, Any]:
    """
    Retrieve ALL financial data for a single ticker in one parallel call.
    
    This meta-tool consolidates data from multiple sources (yfinance, news, SEC,
    earnings, FINRA, Google Trends) and retrieves them in parallel using asyncio.gather
    for maximum efficiency. Now uses the new reliability infrastructure with automatic
    fallback, caching, and health monitoring.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        include_options: Whether to include options data (increases token usage)
        lookback_days: Number of days for historical data (default: 30)
    
    Returns:
        Dictionary with structure:
        {
            "ticker": "AAPL",
            "timestamp": "2025-01-15T10:30:00",
            "data": {
                "info": {...},
                "prices": {...},
                "news": [...],
                "sec_filings": {...},  # Now includes source metadata
                "earnings": {...},     # Now includes source metadata
                "short_volume": {...},
                "google_trends": {...}, # Now includes source metadata
                "options": {...}  # optional
            },
            "errors": [],  # List of partial errors if any source fails
            "metadata": {  # New: metadata about data sources
                "sec_filings": {...},
                "earnings": {...},
                "google_trends": {...}
            }
        }
    
    Example:
        >>> snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        >>> print(f"Retrieved data for {snapshot['ticker']}")
        >>> print(f"Errors: {len(snapshot['errors'])}")
    """
    # Initialize snapshot structure
    snapshot = {
        "ticker": ticker.upper(),
        "timestamp": datetime.now().isoformat(),
        "data": {},
        "errors": [],
        "metadata": {}  # New: store metadata about sources
    }
    
    try:
        # Get manager instances
        sec_manager = _get_sec_manager()
        trends_manager = _get_trends_manager()
        earnings_manager = _get_earnings_manager()
        
        # Create tasks for parallel execution
        tasks = []
        task_names = []
        
        # Task 1: Company info (still using direct yfinance)
        tasks.append(yfinance_source.get_info(ticker))
        task_names.append("info")
        
        # Task 2: Historical prices (map lookback_days to valid yfinance periods)
        # Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        if lookback_days <= 5:
            period = "5d"
        elif lookback_days <= 30:
            period = "1mo"
        elif lookback_days <= 90:
            period = "3mo"
        elif lookback_days <= 180:
            period = "6mo"
        elif lookback_days <= 365:
            period = "1y"
        else:
            period = "2y"
        tasks.append(yfinance_source.get_historical_prices(ticker, period=period))
        task_names.append("prices")
        
        # Task 3: News headlines (still using direct source)
        tasks.append(news_source.get_news_headlines(ticker, limit=5, lookback_days=lookback_days))
        task_names.append("news")
        
        # Task 4: SEC filings (NOW USING SOURCE MANAGER)
        tasks.append(sec_manager.fetch_filings(ticker, ["8-K", "10-Q", "10-K"], lookback_days=lookback_days))
        task_names.append("sec_filings")
        
        # Task 5: Earnings calendar (NOW USING SOURCE MANAGER)
        tasks.append(earnings_manager.fetch_earnings(ticker))
        task_names.append("earnings")
        
        # Task 6: FINRA short volume (uses start_date/end_date, not lookback_days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        tasks.append(finra_source.get_finra_short_volume(ticker, start_date=start_date, end_date=end_date))
        task_names.append("short_volume")
        
        # Task 7: Google Trends (NOW USING SOURCE MANAGER)
        tasks.append(trends_manager.fetch_trends(ticker, window_days=lookback_days))
        task_names.append("google_trends")
        
        # Task 8: Options data (optional)
        if include_options:
            tasks.append(yfinance_source.get_options_expirations(ticker))
            task_names.append("options")
        
        # Execute all tasks in parallel with error handling
        logger.info(f"Fetching {len(tasks)} data sources for {ticker} in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results with graceful degradation
        for task_name, result in zip(task_names, results):
            # Check if result is a DataResult from source managers
            if isinstance(result, DataResult):
                # Extract data and metadata from DataResult
                if result.data is not None:
                    # Success - format and store data compactly
                    snapshot["data"][task_name] = _format_data_compact(task_name, result.data, lookback_days)
                    
                    # Store metadata about the source
                    snapshot["metadata"][task_name] = {
                        "source_used": result.source_used,
                        "is_cached": result.is_cached,
                        "cache_age_seconds": result.cache_age_seconds,
                        "is_stale": result.is_stale,
                        "attempted_sources": result.attempted_sources,
                        "successful_sources": result.successful_sources,
                        "failed_sources": result.failed_sources,
                        "partial_data": result.partial_data,
                        "last_successful_update": result.last_successful_update.isoformat() if result.last_successful_update else None
                    }
                    
                    logger.debug(
                        f"Successfully fetched {task_name} for {ticker} from {result.source_used} "
                        f"(cached: {result.is_cached}, stale: {result.is_stale})"
                    )
                    
                    # Add errors from DataResult if any
                    for error_info in result.errors:
                        error_msg = (
                            f"{task_name} ({error_info.source}): {error_info.error_message} "
                            f"[{error_info.suggested_action}]"
                        )
                        snapshot["errors"].append(error_msg)
                else:
                    # No data available
                    error_msg = f"{task_name}: No data available from any source"
                    snapshot["errors"].append(error_msg)
                    
                    # Still store metadata about the attempt
                    snapshot["metadata"][task_name] = {
                        "source_used": "none",
                        "attempted_sources": result.attempted_sources,
                        "failed_sources": result.failed_sources,
                        "errors": [
                            {
                                "source": err.source,
                                "type": err.error_type,
                                "message": err.error_message,
                                "suggested_action": err.suggested_action
                            }
                            for err in result.errors
                        ]
                    }
                    
                    logger.warning(f"No data available for {task_name} for {ticker}")
            
            elif isinstance(result, Exception):
                # Log error and continue with other sources
                error_msg = f"{task_name}: {type(result).__name__} - {str(result)}"
                snapshot["errors"].append(error_msg)
                logger.warning(f"Error fetching {task_name} for {ticker}: {result}")
            
            elif result is None or (isinstance(result, (list, dict)) and not result):
                # Empty result from direct sources
                snapshot["errors"].append(f"{task_name}: No data available")
                logger.info(f"No data available for {task_name} for {ticker}")
            
            else:
                # Success from direct sources - format and store data compactly
                snapshot["data"][task_name] = _format_data_compact(task_name, result, lookback_days)
                logger.debug(f"Successfully fetched {task_name} for {ticker}")
        
        logger.info(
            f"Snapshot complete for {ticker}: {len(snapshot['data'])} sources, "
            f"{len(snapshot['errors'])} errors"
        )
        
    except Exception as e:
        # Catch-all for unexpected errors
        error_msg = f"Unexpected error in get_financial_snapshot: {type(e).__name__} - {str(e)}"
        snapshot["errors"].append(error_msg)
        logger.error(error_msg)
    
    return snapshot


async def get_multi_ticker_snapshot(
    tickers: List[str],
    include_options: bool = False,
    lookback_days: int = 30,
    max_tickers: int = 10
) -> Dict[str, Any]:
    """
    Retrieve financial snapshots for MULTIPLE tickers in parallel.
    
    This meta-tool analyzes multiple tickers simultaneously using asyncio.gather
    for maximum efficiency. It limits the number of tickers to prevent timeouts
    and handles errors gracefully on a per-ticker basis.
    
    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        include_options: Whether to include options data (increases token usage)
        lookback_days: Number of days for historical data (default: 30)
        max_tickers: Maximum number of tickers to analyze (default: 10)
    
    Returns:
        Dictionary with structure:
        {
            "timestamp": "2025-01-15T10:30:00",
            "tickers_count": 3,
            "snapshots": {
                "AAPL": {...},  # Full snapshot for each ticker
                "MSFT": {...},
                "GOOGL": {...}
            },
            "global_errors": []  # Errors that affected multiple tickers
        }
    
    Example:
        >>> multi_snapshot = await get_multi_ticker_snapshot(
        ...     ["AAPL", "MSFT", "GOOGL"],
        ...     lookback_days=7
        ... )
        >>> print(f"Analyzed {multi_snapshot['tickers_count']} tickers")
        >>> print(f"Successful: {len(multi_snapshot['snapshots'])}")
    """
    # Initialize multi-snapshot structure
    multi_snapshot = {
        "timestamp": datetime.now().isoformat(),
        "tickers_count": 0,
        "snapshots": {},
        "global_errors": []
    }
    
    try:
        # Validate and clean ticker list
        if not tickers or not isinstance(tickers, list):
            multi_snapshot["global_errors"].append("Invalid tickers list provided")
            return multi_snapshot
        
        # Clean and uppercase tickers
        clean_tickers = [ticker.strip().upper() for ticker in tickers if ticker and ticker.strip()]
        
        if not clean_tickers:
            multi_snapshot["global_errors"].append("No valid tickers provided after cleaning")
            return multi_snapshot
        
        # Limit to max_tickers to avoid timeouts
        if len(clean_tickers) > max_tickers:
            logger.warning(f"Limiting analysis from {len(clean_tickers)} to {max_tickers} tickers")
            multi_snapshot["global_errors"].append(
                f"Ticker list limited from {len(clean_tickers)} to {max_tickers} to prevent timeout"
            )
            clean_tickers = clean_tickers[:max_tickers]
        
        multi_snapshot["tickers_count"] = len(clean_tickers)
        
        # Create tasks for parallel execution
        logger.info(f"Creating parallel tasks for {len(clean_tickers)} tickers...")
        tasks = [
            get_financial_snapshot(ticker, include_options, lookback_days)
            for ticker in clean_tickers
        ]
        
        # Execute all ticker snapshots in parallel with error handling
        logger.info(f"Executing {len(tasks)} ticker snapshots in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results with per-ticker error handling
        for ticker, result in zip(clean_tickers, results):
            if isinstance(result, Exception):
                # Ticker-level error - log and continue with others
                error_msg = f"{ticker}: {type(result).__name__} - {str(result)}"
                multi_snapshot["global_errors"].append(error_msg)
                logger.error(f"Failed to fetch snapshot for {ticker}: {result}")
            elif result is None:
                # Unexpected None result
                multi_snapshot["global_errors"].append(f"{ticker}: Returned None (unexpected)")
                logger.warning(f"Snapshot for {ticker} returned None")
            else:
                # Success - store the snapshot
                multi_snapshot["snapshots"][ticker] = result
                logger.debug(f"Successfully fetched snapshot for {ticker}")
        
        # Log summary
        successful = len(multi_snapshot["snapshots"])
        failed = len(multi_snapshot["global_errors"])
        logger.info(
            f"Multi-ticker snapshot complete: {successful} successful, "
            f"{failed} errors out of {len(clean_tickers)} tickers"
        )
        
    except Exception as e:
        # Catch-all for unexpected errors
        error_msg = f"Unexpected error in get_multi_ticker_snapshot: {type(e).__name__} - {str(e)}"
        multi_snapshot["global_errors"].append(error_msg)
        logger.error(error_msg)
    
    return multi_snapshot


def format_snapshot_for_llm(snapshot: Dict[str, Any]) -> str:
    """
    Format a financial snapshot into compact text optimized for LLM consumption.
    
    This function converts the structured snapshot data into a human-readable
    text format with clear sections, truncated content, and error indicators.
    Now includes source metadata, cache status, and fallback information.
    Optimized to save 50-70% tokens compared to raw JSON format.
    
    Args:
        snapshot: Financial snapshot dictionary from get_financial_snapshot()
    
    Returns:
        Formatted text string with all financial data in compact sections
    
    Example:
        >>> snapshot = await get_financial_snapshot("AAPL")
        >>> formatted = format_snapshot_for_llm(snapshot)
        >>> print(formatted)
        === FINANCIAL SNAPSHOT: AAPL ===
        Timestamp: 2025-01-15T10:30:00
        ...
    """
    lines = []
    ticker = snapshot.get("ticker", "UNKNOWN")
    timestamp = snapshot.get("timestamp", "")
    data = snapshot.get("data", {})
    errors = snapshot.get("errors", [])
    metadata = snapshot.get("metadata", {})
    
    # Header
    lines.append(f"=== FINANCIAL SNAPSHOT: {ticker} ===")
    lines.append(f"Timestamp: {timestamp}")
    
    # Data source summary (if metadata available)
    if metadata:
        lines.append("")
        lines.append("--- DATA SOURCES ---")
        for data_type, meta in metadata.items():
            source_used = meta.get("source_used", "unknown")
            is_cached = meta.get("is_cached", False)
            is_stale = meta.get("is_stale", False)
            cache_age = meta.get("cache_age_seconds")
            
            # Format cache status
            if is_cached:
                if is_stale:
                    cache_status = f"⚠️ STALE CACHE (age: {cache_age}s)"
                else:
                    cache_status = f"✓ CACHED (age: {cache_age}s)"
            else:
                cache_status = "✓ FRESH"
            
            lines.append(f"{data_type}: {source_used} [{cache_status}]")
            
            # Show fallback info if multiple sources were attempted
            attempted = meta.get("attempted_sources", [])
            if len(attempted) > 1:
                failed = meta.get("failed_sources", [])
                if failed:
                    lines.append(f"  └─ Fallback used (failed: {', '.join(failed)})")
    
    lines.append("")
    
    # Section 1: Company Info
    info = data.get("info", {})
    if info:
        lines.append("--- COMPANY INFORMATION ---")
        lines.append(f"Company: {info.get('longName', 'N/A')}")
        lines.append(f"Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}")
        
        # Market Cap formatting
        market_cap = info.get('marketCap')
        if market_cap:
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                market_cap_str = f"${market_cap/1e9:.2f}B"
            elif market_cap >= 1e6:
                market_cap_str = f"${market_cap/1e6:.2f}M"
            else:
                market_cap_str = f"${market_cap:,.0f}"
        else:
            market_cap_str = "N/A"
        
        current_price = info.get('currentPrice', 'N/A')
        lines.append(f"Market Cap: {market_cap_str} | Price: ${current_price}")
        
        # Additional metrics
        pe_ratio = info.get('trailingPE')
        forward_pe = info.get('forwardPE')
        beta = info.get('beta')
        div_yield = info.get('dividendYield')
        
        metrics = []
        if pe_ratio:
            metrics.append(f"P/E: {pe_ratio:.2f}")
        if forward_pe:
            metrics.append(f"Fwd P/E: {forward_pe:.2f}")
        if beta:
            metrics.append(f"Beta: {beta:.2f}")
        if div_yield:
            metrics.append(f"Div Yield: {div_yield*100:.2f}%")
        
        if metrics:
            lines.append(" | ".join(metrics))
        
        # Summary
        summary = info.get('summary', '')
        if summary:
            lines.append(f"Summary: {summary}")
        
        lines.append("")
    
    # Section 2: Price Data
    prices = data.get("prices", {})
    if prices:
        lines.append("--- PRICE DATA ---")
        latest_close = prices.get('latest_close')
        latest_date = prices.get('latest_date')
        change_30d = prices.get('change_30d_pct')
        
        if latest_close:
            lines.append(f"Latest Close: ${latest_close:.2f} (as of {latest_date})")
        
        if change_30d is not None:
            direction = "↑" if change_30d > 0 else "↓" if change_30d < 0 else "→"
            lines.append(f"30-day Change: {direction} {change_30d:+.2f}%")
        
        lines.append("")
    
    # Section 3: News (max 3 articles)
    news = data.get("news", [])
    if news:
        # Handle both list and dict formats
        articles = news.get("articles", news) if isinstance(news, dict) else news
        total_available = news.get("total_available", len(articles)) if isinstance(news, dict) else len(articles)
        
        lines.append(f"--- RECENT NEWS ({total_available} articles) ---")
        
        # Display max 3 articles
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')
            source = article.get('source', 'Unknown')
            published = article.get('published_at', '')
            lines.append(f"{i}. {title} ({source})")
            if published:
                lines.append(f"   Published: {published}")
        
        if total_available > 3:
            lines.append(f"   ... and {total_available - 3} more articles")
        
        lines.append("")
    
    # Section 4: SEC Filings (max 2)
    sec_filings = data.get("sec_filings", [])
    if sec_filings:
        # Handle both list and dict formats
        filings = sec_filings.get("filings", sec_filings) if isinstance(sec_filings, dict) else sec_filings
        total_available = sec_filings.get("total_available", len(filings)) if isinstance(sec_filings, dict) else len(filings)
        
        lines.append(f"--- RECENT SEC FILINGS ({total_available} total) ---")
        
        # Display max 2 filings
        for i, filing in enumerate(filings[:2], 1):
            form = filing.get('form', 'N/A')
            date = filing.get('date', 'N/A')
            title = filing.get('title', 'No title')
            lines.append(f"{i}. {form} - {date}")
            lines.append(f"   {title}")
        
        if total_available > 2:
            lines.append(f"   ... and {total_available - 2} more filings")
        
        lines.append("")
    
    # Section 5: Earnings
    earnings = data.get("earnings", [])
    if earnings:
        # Handle both list and dict formats
        earnings_data = earnings.get("recent_earnings", earnings) if isinstance(earnings, dict) else earnings
        
        lines.append("--- EARNINGS ---")
        
        # Try to identify next earnings vs historical
        if earnings_data:
            # Assume first is most recent/upcoming
            next_earnings = earnings_data[0]
            lines.append(f"Next Earnings: {next_earnings.get('date', 'N/A')}")
            
            # Show recent performance summary (up to 3 historical)
            if len(earnings_data) > 1:
                lines.append("Recent Performance:")
                for earning in earnings_data[1:4]:  # Skip first (next), show up to 3 historical
                    date = earning.get('date', 'N/A')
                    eps_actual = earning.get('epsActual', earning.get('eps_actual'))
                    eps_estimate = earning.get('epsEstimate', earning.get('eps_estimate'))
                    
                    if eps_actual and eps_estimate:
                        beat = "Beat" if eps_actual > eps_estimate else "Miss" if eps_actual < eps_estimate else "Met"
                        lines.append(f"  {date}: ${eps_actual:.2f} vs ${eps_estimate:.2f} est. ({beat})")
                    elif eps_actual:
                        lines.append(f"  {date}: ${eps_actual:.2f}")
        
        lines.append("")
    
    # Section 6: Short Volume
    short_volume = data.get("short_volume", {})
    if short_volume and isinstance(short_volume, dict):
        lines.append("--- SHORT VOLUME ---")
        
        avg_ratio = short_volume.get('average_short_ratio')
        recent_ratio = short_volume.get('recent_short_ratio')
        trend = short_volume.get('trend', 'unknown')
        days = short_volume.get('days_analyzed', 0)
        
        if avg_ratio:
            lines.append(f"Average Short Ratio: {avg_ratio:.2%} ({days} days)")
        if recent_ratio:
            lines.append(f"Recent Short Ratio: {recent_ratio:.2%}")
        if trend:
            trend_symbol = "↑" if trend == "increasing" else "↓" if trend == "decreasing" else "→"
            lines.append(f"Trend: {trend_symbol} {trend.capitalize()}")
        
        lines.append("")
    
    # Section 7: Google Trends
    google_trends = data.get("google_trends", {})
    if google_trends and isinstance(google_trends, dict):
        lines.append("--- SEARCH INTEREST (Google Trends) ---")
        
        latest = google_trends.get('latest', 0)
        average = google_trends.get('average', 0)
        trend = google_trends.get('trend', 'unknown')
        timeframe = google_trends.get('timeframe', '')
        
        lines.append(f"Latest Interest: {latest}/100")
        lines.append(f"Average Interest: {average:.1f}/100")
        
        if trend:
            trend_symbol = "↑" if trend == "increasing" else "↓" if trend == "decreasing" else "→"
            lines.append(f"Trend: {trend_symbol} {trend.capitalize()}")
        
        if timeframe:
            lines.append(f"Timeframe: {timeframe}")
        
        lines.append("")
    
    # Error section (if any)
    if errors:
        lines.append(f"⚠️ Partial data - {len(errors)} error(s) occurred:")
        for error in errors[:5]:  # Show max 5 errors
            lines.append(f"  • {error}")
        if len(errors) > 5:
            lines.append(f"  ... and {len(errors) - 5} more errors")
        lines.append("")
    
    # Detailed error information from metadata (if available)
    detailed_errors = []
    for data_type, meta in metadata.items():
        if "errors" in meta and meta["errors"]:
            for err in meta["errors"]:
                detailed_errors.append({
                    "data_type": data_type,
                    "source": err.get("source", "unknown"),
                    "type": err.get("type", "unknown"),
                    "message": err.get("message", ""),
                    "action": err.get("suggested_action", "")
                })
    
    if detailed_errors:
        lines.append("--- DETAILED ERROR INFORMATION ---")
        for i, err in enumerate(detailed_errors[:3], 1):  # Show max 3 detailed errors
            lines.append(f"{i}. {err['data_type']} - {err['source']}")
            lines.append(f"   Type: {err['type']}")
            lines.append(f"   Message: {err['message']}")
            lines.append(f"   💡 Suggested Action: {err['action']}")
        
        if len(detailed_errors) > 3:
            lines.append(f"   ... and {len(detailed_errors) - 3} more detailed errors")
        lines.append("")
    
    return "\n".join(lines)


def format_multi_snapshot_for_llm(multi_snapshot: Dict[str, Any]) -> str:
    """
    Format a multi-ticker snapshot into compact text optimized for LLM consumption.
    
    This function converts multiple ticker snapshots into a consolidated text format
    with clear sections for each ticker, avoiding repetition and optimizing for
    token efficiency.
    
    Args:
        multi_snapshot: Multi-ticker snapshot dictionary from get_multi_ticker_snapshot()
    
    Returns:
        Formatted text string with all tickers' financial data in compact sections
    
    Example:
        >>> multi_snapshot = await get_multi_ticker_snapshot(["AAPL", "MSFT", "GOOGL"])
        >>> formatted = format_multi_snapshot_for_llm(multi_snapshot)
        >>> print(formatted)
        === MULTI-TICKER ANALYSIS ===
        Timestamp: 2025-01-15T10:30:00
        Tickers Analyzed: 3
        ...
    """
    lines = []
    timestamp = multi_snapshot.get("timestamp", "")
    tickers_count = multi_snapshot.get("tickers_count", 0)
    snapshots = multi_snapshot.get("snapshots", {})
    global_errors = multi_snapshot.get("global_errors", [])
    
    # Header
    lines.append("=== MULTI-TICKER ANALYSIS ===")
    lines.append(f"Timestamp: {timestamp}")
    lines.append(f"Tickers Analyzed: {tickers_count}")
    lines.append(f"Successful: {len(snapshots)}")
    
    if global_errors:
        lines.append(f"Errors: {len(global_errors)}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("")
    
    # Format each ticker snapshot
    if snapshots:
        for i, (ticker, snapshot) in enumerate(snapshots.items(), 1):
            # Add separator between tickers (except for first)
            if i > 1:
                lines.append("")
                lines.append("-" * 60)
                lines.append("")
            
            # Format individual snapshot
            formatted_snapshot = format_snapshot_for_llm(snapshot)
            lines.append(formatted_snapshot)
    else:
        lines.append("⚠️ No ticker data available")
        lines.append("")
    
    # Global errors section (if any)
    if global_errors:
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"⚠️ GLOBAL ERRORS ({len(global_errors)}):")
        lines.append("")
        
        # Show all global errors (they're already per-ticker, so should be limited)
        for i, error in enumerate(global_errors, 1):
            lines.append(f"{i}. {error}")
        
        lines.append("")
    
    # Footer with summary
    lines.append("=" * 60)
    lines.append(f"END OF MULTI-TICKER ANALYSIS ({len(snapshots)}/{tickers_count} successful)")
    
    return "\n".join(lines)


def _format_data_compact(data_type: str, data: Any, lookback_days: int) -> Any:
    """
    Format data in a compact way to save tokens.
    
    Args:
        data_type: Type of data (info, prices, news, etc.)
        data: Raw data from datasource
        lookback_days: Lookback period for context
    
    Returns:
        Compactly formatted data
    """
    try:
        if data_type == "info":
            # Truncate company summary and keep essential fields
            if isinstance(data, dict):
                compact_info = {
                    "longName": data.get("longName", ""),
                    "sector": data.get("sector", ""),
                    "industry": data.get("industry", ""),
                    "marketCap": data.get("marketCap"),
                    "currentPrice": data.get("currentPrice"),
                    "fiftyTwoWeekHigh": data.get("fiftyTwoWeekHigh"),
                    "fiftyTwoWeekLow": data.get("fiftyTwoWeekLow"),
                    "averageVolume": data.get("averageVolume"),
                    "beta": data.get("beta"),
                    "trailingPE": data.get("trailingPE"),
                    "forwardPE": data.get("forwardPE"),
                    "dividendYield": data.get("dividendYield"),
                    "summary": truncate_string(data.get("longBusinessSummary", ""), max_length=300)
                }
                return compact_info
            return data
        
        elif data_type == "prices":
            # Keep only last 5 days + calculate 30-day change
            if hasattr(data, 'tail'):  # pandas DataFrame
                last_5 = data.tail(5)
                
                # Calculate 30-day change if we have enough data
                change_30d_pct = None
                if len(data) >= 2:
                    first_close = data['Close'].iloc[0]
                    last_close = data['Close'].iloc[-1]
                    if first_close and first_close != 0:
                        change_30d_pct = round(((last_close - first_close) / first_close) * 100, 2)
                
                # Convert to compact dict format
                compact_prices = {
                    "latest_close": float(last_5['Close'].iloc[-1]) if len(last_5) > 0 else None,
                    "latest_date": str(last_5.index[-1].date()) if len(last_5) > 0 else None,
                    "change_30d_pct": change_30d_pct,
                    "last_5_days": [
                        {
                            "date": str(row.name.date()),
                            "close": round(float(row['Close']), 2),
                            "volume": int(row['Volume'])
                        }
                        for _, row in last_5.iterrows()
                    ]
                }
                return compact_prices
            return data
        
        elif data_type == "news":
            # Limit to 5 articles with truncated summaries
            if isinstance(data, list):
                compact_news = []
                for article in data[:5]:
                    compact_article = {
                        "published_at": article.get("published_at", ""),
                        "source": article.get("source", ""),
                        "title": truncate_string(article.get("title", ""), max_length=150),
                        "url": article.get("url", ""),
                        "summary": truncate_string(article.get("summary", ""), max_length=150)
                    }
                    compact_news.append(compact_article)
                
                if len(data) > 5:
                    return {"articles": compact_news, "total_available": len(data)}
                return compact_news
            return data
        
        elif data_type == "sec_filings":
            # Limit to 3 most recent filings
            if isinstance(data, list):
                compact_filings = []
                for filing in data[:3]:
                    compact_filing = {
                        "date": filing.get("date", ""),
                        "form": filing.get("form", ""),
                        "title": truncate_string(filing.get("title", ""), max_length=100),
                        "url": filing.get("url", "")
                    }
                    compact_filings.append(compact_filing)
                
                if len(data) > 3:
                    return {"filings": compact_filings, "total_available": len(data)}
                return compact_filings
            return data
        
        elif data_type == "earnings":
            # Keep next earnings + 3 recent quarters
            if isinstance(data, list):
                # Sort by date to get most recent
                sorted_earnings = sorted(data, key=lambda x: x.get("date", ""), reverse=True)
                compact_earnings = sorted_earnings[:4]  # Next + 3 recent
                
                if len(data) > 4:
                    return {"recent_earnings": compact_earnings, "total_available": len(data)}
                return compact_earnings
            return data
        
        elif data_type == "short_volume":
            # Return only aggregated metrics, not daily data
            if isinstance(data, list) and data:
                # Calculate aggregate metrics
                total_short = sum(d.get("short_volume", 0) for d in data)
                total_volume = sum(d.get("total_volume", 0) for d in data)
                avg_ratio = sum(d.get("short_ratio", 0) for d in data) / len(data)
                
                # Recent vs historical
                recent = data[:5] if len(data) >= 5 else data
                recent_avg_ratio = sum(d.get("short_ratio", 0) for d in recent) / len(recent) if recent else 0
                
                return {
                    "average_short_ratio": round(avg_ratio, 4),
                    "recent_short_ratio": round(recent_avg_ratio, 4),
                    "trend": "increasing" if recent_avg_ratio > avg_ratio else "decreasing",
                    "days_analyzed": len(data),
                    "latest_date": data[0].get("date", "") if data else ""
                }
            return data
        
        elif data_type == "google_trends":
            # Return only summary metrics, not full series
            if isinstance(data, dict):
                compact_trends = {
                    "latest": data.get("latest", 0),
                    "average": data.get("average", 0),
                    "trend": data.get("trend", "unknown"),
                    "peak_value": data.get("peak_value", 0),
                    "peak_date": data.get("peak_date", ""),
                    "timeframe": data.get("timeframe", "")
                }
                return compact_trends
            return data
        
        elif data_type == "options":
            # Return only expiration dates, not full chain
            if isinstance(data, (tuple, list)):
                return {
                    "available_expirations": list(data)[:10],  # Limit to 10
                    "total_expirations": len(data)
                }
            return data
        
        else:
            # Unknown data type - return as is
            return data
            
    except Exception as e:
        logger.warning(f"Error formatting {data_type}: {e}")
        return data
