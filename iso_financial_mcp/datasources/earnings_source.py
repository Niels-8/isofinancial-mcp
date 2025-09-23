"""
Earnings Calendar data client
Handles Yahoo Finance/Nasdaq earnings data scraping with caching
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from cachetools import TTLCache
from asyncio_throttle import Throttler
import logging
from .validation import validate_ticker, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache with 24-hour TTL as per requirements
earnings_cache = TTLCache(maxsize=500, ttl=86400)  # 24 hours = 86400 seconds

# Rate limiter for earnings data (3 requests per second to be conservative)
earnings_throttler = Throttler(rate_limit=3, period=1.0)

class EarningsError(Exception):
    """Custom exception for earnings data errors"""
    pass

async def get_earnings_calendar(ticker: str) -> List[Dict[str, Any]]:
    """
    Retrieve earnings calendar data with EPS estimates, actuals, and timing.
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        List of earnings dictionaries with date, period, estimates, actuals, and timing
    """
    try:
        # Validate input
        ticker = validate_ticker(ticker)
        
        # Create cache key
        cache_key = f"earnings_{ticker}"
        
        # Check cache first
        if cache_key in earnings_cache:
            logger.info(f"Earnings calendar cache hit for {ticker}")
            return earnings_cache[cache_key]
        
        # Apply rate limiting
        async with earnings_throttler:
            earnings_data = await _fetch_earnings_calendar(ticker)
            
        # Cache the results
        earnings_cache[cache_key] = earnings_data
        logger.info(f"Earnings calendar fetched and cached for {ticker}: {len(earnings_data)} records")
        
        return earnings_data
        
    except ValidationError as e:
        logger.error(f"Validation error for ticker {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching earnings calendar for {ticker}: {e}")
        # Return empty list on error for graceful degradation
        return []

async def _fetch_earnings_calendar(ticker: str) -> List[Dict[str, Any]]:
    """
    Internal function to fetch earnings calendar data from multiple sources.
    """
    earnings_data = []
    
    # Try Yahoo Finance first
    yahoo_data = await _fetch_yahoo_earnings(ticker)
    if yahoo_data:
        earnings_data.extend(yahoo_data)
    
    # If Yahoo Finance fails or returns limited data, try alternative sources
    if not earnings_data:
        nasdaq_data = await _fetch_nasdaq_earnings(ticker)
        if nasdaq_data:
            earnings_data.extend(nasdaq_data)
    
    # Sort by date (most recent first)
    earnings_data.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return earnings_data

async def _fetch_yahoo_earnings(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetch earnings data from Yahoo Finance.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # Yahoo Finance earnings calendar URL
            url = f"https://finance.yahoo.com/calendar/earnings?symbol={ticker}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Yahoo Finance returned status {response.status} for {ticker}")
                    return []
                
                html = await response.text()
                
            # Parse HTML to extract earnings data
            soup = BeautifulSoup(html, 'html.parser')
            
            earnings_data = []
            
            # Look for earnings data in various possible formats
            # Yahoo Finance structure can vary, so we try multiple approaches
            
            # Method 1: Look for JSON data in script tags
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'earnings' in script.string.lower():
                    try:
                        # Extract JSON data from script
                        json_match = re.search(r'root\.App\.main\s*=\s*({.*?});', script.string)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            earnings_info = _extract_yahoo_earnings_from_json(data, ticker)
                            if earnings_info:
                                earnings_data.extend(earnings_info)
                                break
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # Method 2: Parse HTML tables if JSON method fails
            if not earnings_data:
                earnings_data = _parse_yahoo_earnings_table(soup, ticker)
            
            return earnings_data
            
    except Exception as e:
        logger.error(f"Error fetching Yahoo earnings for {ticker}: {e}")
        return []

def _extract_yahoo_earnings_from_json(data: Dict, ticker: str) -> List[Dict[str, Any]]:
    """
    Extract earnings data from Yahoo Finance JSON structure.
    """
    try:
        # Navigate through Yahoo's complex JSON structure
        # This is a simplified version - actual structure may vary
        earnings_data = []
        
        # Look for earnings-related data in the JSON
        if 'context' in data and 'dispatcher' in data['context']:
            stores = data['context']['dispatcher']['stores']
            
            # Look for earnings store
            for store_name, store_data in stores.items():
                if 'earnings' in store_name.lower() or 'calendar' in store_name.lower():
                    if isinstance(store_data, dict) and 'earnings' in store_data:
                        earnings_list = store_data['earnings']
                        
                        for earning in earnings_list:
                            if earning.get('ticker', '').upper() == ticker.upper():
                                earnings_data.append(_format_earnings_record(earning))
        
        return earnings_data
        
    except Exception as e:
        logger.debug(f"Error extracting Yahoo earnings JSON for {ticker}: {e}")
        return []

def _parse_yahoo_earnings_table(soup: BeautifulSoup, ticker: str) -> List[Dict[str, Any]]:
    """
    Parse earnings data from Yahoo Finance HTML tables.
    """
    try:
        earnings_data = []
        
        # Look for earnings tables
        tables = soup.find_all('table')
        
        # Ensure tables is a valid list
        if tables is None:
            logger.warning(f"No tables found in Yahoo earnings page for {ticker}")
            return []
        
        for table in tables:
            if table is None:
                continue
                
            rows = table.find_all('tr')
            
            # Ensure rows is a valid list and not None
            if rows is None:
                logger.debug(f"No rows found in table for {ticker}")
                continue
            
            for row in rows:
                if row is None:
                    continue
                    
                cells = row.find_all(['td', 'th'])
                
                # Ensure cells is a valid list
                if cells is None or len(cells) < 4:
                    continue
                
                # Try to extract earnings information
                try:
                    cell_texts = [cell.get_text(strip=True) for cell in cells if cell is not None]
                    
                    # Look for ticker symbol in the row
                    if any(ticker.upper() in text.upper() for text in cell_texts):
                        earnings_record = _parse_earnings_row(cell_texts, ticker)
                        if earnings_record:
                            earnings_data.append(earnings_record)
                except Exception as e:
                    logger.debug(f"Error extracting cell text for {ticker}: {e}")
                    continue
        
        return earnings_data
        
    except Exception as e:
        logger.debug(f"Error parsing Yahoo earnings table for {ticker}: {e}")
        return []

async def _fetch_nasdaq_earnings(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetch earnings data from Nasdaq as alternative source.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # Nasdaq earnings API endpoint
            url = f"https://api.nasdaq.com/api/calendar/earnings?date=2024-01-01&date=2024-12-31"
            
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
            # Parse Nasdaq earnings data
            earnings_data = []
            
            # Safely access nested data structure
            if 'data' in data and isinstance(data['data'], dict) and 'rows' in data['data']:
                rows = data['data']['rows']
                # Ensure rows is iterable and not None
                if rows is not None and hasattr(rows, '__iter__'):
                    for row in rows:
                        if isinstance(row, dict) and row.get('symbol', '').upper() == ticker.upper():
                            earnings_record = _format_nasdaq_earnings(row)
                            if earnings_record:
                                earnings_data.append(earnings_record)
                else:
                    logger.warning(f"Nasdaq API returned non-iterable rows data for {ticker}: {type(rows)}")
            else:
                logger.warning(f"Nasdaq API returned unexpected data structure for {ticker}: missing 'data' or 'rows' keys")
            
            return earnings_data
            
    except Exception as e:
        logger.error(f"Error fetching Nasdaq earnings for {ticker}: {e}")
        return []

def _format_earnings_record(earning_data: Dict) -> Dict[str, Any]:
    """
    Format earnings record into standardized structure.
    """
    try:
        # Determine timing (BMO = Before Market Open, AMC = After Market Close)
        timing = "N/A"
        time_str = earning_data.get('time', '').lower()
        if 'bmo' in time_str or 'before' in time_str:
            timing = "BMO"
        elif 'amc' in time_str or 'after' in time_str:
            timing = "AMC"
        
        return {
            "date": earning_data.get('date', ''),
            "period": earning_data.get('period', ''),
            "eps_estimate": earning_data.get('epsEstimate'),
            "eps_actual": earning_data.get('epsActual'),
            "eps_surprise": earning_data.get('epsSurprise'),
            "surprise_percentage": earning_data.get('surprisePercentage'),
            "timing": timing,
            "revenue_estimate": earning_data.get('revenueEstimate'),
            "revenue_actual": earning_data.get('revenueActual')
        }
        
    except Exception as e:
        logger.debug(f"Error formatting earnings record: {e}")
        return {}

def _format_nasdaq_earnings(row_data: Dict) -> Dict[str, Any]:
    """
    Format Nasdaq earnings data into standardized structure.
    """
    try:
        return {
            "date": row_data.get('date', ''),
            "period": row_data.get('fiscalQuarterEnding', ''),
            "eps_estimate": _safe_float(row_data.get('eps_estimate')),
            "eps_actual": _safe_float(row_data.get('eps')),
            "eps_surprise": _safe_float(row_data.get('surprise')),
            "surprise_percentage": _safe_float(row_data.get('surprisePercentage')),
            "timing": row_data.get('time', 'N/A'),
            "revenue_estimate": _safe_float(row_data.get('revenueEstimate')),
            "revenue_actual": _safe_float(row_data.get('revenue'))
        }
        
    except Exception as e:
        logger.debug(f"Error formatting Nasdaq earnings: {e}")
        return {}

def _parse_earnings_row(cell_texts: List[str], ticker: str) -> Optional[Dict[str, Any]]:
    """
    Parse earnings data from table row cells.
    """
    try:
        # This is a simplified parser - actual implementation would need
        # to handle various table formats from different sources
        
        if len(cell_texts) < 4:
            return None
        
        # Try to identify date, EPS estimate, EPS actual, etc.
        date_pattern = r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}'
        eps_pattern = r'[-+]?\d*\.?\d+'
        
        date = ""
        eps_estimate = None
        eps_actual = None
        
        for text in cell_texts:
            if re.search(date_pattern, text):
                date = text
            elif '$' in text and re.search(eps_pattern, text):
                # Try to extract EPS values
                eps_match = re.search(eps_pattern, text.replace('$', ''))
                if eps_match:
                    if eps_estimate is None:
                        eps_estimate = float(eps_match.group())
                    elif eps_actual is None:
                        eps_actual = float(eps_match.group())
        
        if date:
            return {
                "date": date,
                "period": "N/A",
                "eps_estimate": eps_estimate,
                "eps_actual": eps_actual,
                "eps_surprise": (eps_actual - eps_estimate) if eps_actual and eps_estimate else None,
                "surprise_percentage": ((eps_actual - eps_estimate) / eps_estimate * 100) if eps_actual and eps_estimate and eps_estimate != 0 else None,
                "timing": "N/A",
                "revenue_estimate": None,
                "revenue_actual": None
            }
        
        return None
        
    except Exception as e:
        logger.debug(f"Error parsing earnings row: {e}")
        return None

def _safe_float(value: Any) -> Optional[float]:
    """
    Safely convert value to float.
    """
    if value is None:
        return None
    
    try:
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[$,]', '', value)
            return float(cleaned)
        return float(value)
    except (ValueError, TypeError):
        return None

# Utility functions
def clear_earnings_cache():
    """Clear the earnings calendar cache"""
    earnings_cache.clear()
    logger.info("Earnings calendar cache cleared")

def get_cache_stats() -> Dict[str, Any]:
    """Get earnings cache statistics"""
    return {
        "cache_size": len(earnings_cache),
        "max_size": earnings_cache.maxsize,
        "ttl": earnings_cache.ttl,
        "hits": getattr(earnings_cache, 'hits', 0),
        "misses": getattr(earnings_cache, 'misses', 0)
    }

def get_upcoming_earnings(earnings_data: List[Dict[str, Any]], days_ahead: int = 30) -> List[Dict[str, Any]]:
    """
    Filter earnings data to show only upcoming earnings within specified days.
    """
    today = datetime.now().date()
    cutoff_date = today + timedelta(days=days_ahead)
    
    upcoming = []
    
    for earning in earnings_data:
        try:
            # Parse various date formats
            date_str = earning.get("date", "")
            if not date_str:
                continue
            
            # Try different date formats
            earning_date = None
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    earning_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if earning_date and today <= earning_date <= cutoff_date:
                upcoming.append(earning)
                
        except Exception as e:
            logger.debug(f"Error parsing earnings date: {e}")
            continue
    
    return upcoming