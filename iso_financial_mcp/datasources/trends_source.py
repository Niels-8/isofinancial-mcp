"""
Google Trends data client
Handles pytrends integration for search volume data with caching and rate limiting
"""

import asyncio
from pytrends.request import TrendReq
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from cachetools import TTLCache
from asyncio_throttle import Throttler
import logging
import pandas as pd
import warnings

# Suppress pandas FutureWarnings from pytrends
warnings.filterwarnings('ignore', category=FutureWarning, module='pytrends')
warnings.filterwarnings('ignore', category=FutureWarning, message='.*pandas.*')
warnings.filterwarnings('ignore', category=FutureWarning, message='.*count.*positional.*')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache with 24-hour TTL as per requirements
trends_cache = TTLCache(maxsize=500, ttl=86400)  # 24 hours = 86400 seconds

# Rate limiter for Google Trends (2 requests per second to be very conservative)
trends_throttler = Throttler(rate_limit=2, period=1.0)

class TrendsError(Exception):
    """Custom exception for Google Trends errors"""
    pass

async def get_google_trends(
    term: str,
    window_days: int = 30
) -> Dict[str, Any]:
    """
    Retrieve Google Trends search volume data with caching and rate limiting.
    
    Args:
        term: Search term (typically ticker symbol or company name)
        window_days: Time window in days for trend analysis (default: 30)
    
    Returns:
        Dictionary with series data and latest value
    """
    # Create cache key
    cache_key = f"trends_{term}_{window_days}"
    
    # Check cache first
    if cache_key in trends_cache:
        logger.info(f"Google Trends cache hit for {term}")
        return trends_cache[cache_key]
    
    try:
        # Apply rate limiting
        async with trends_throttler:
            trends_data = await _fetch_google_trends(term, window_days)
            
        # Cache the results
        trends_cache[cache_key] = trends_data
        logger.info(f"Google Trends fetched and cached for {term}")
        
        return trends_data
        
    except Exception as e:
        logger.error(f"Error fetching Google Trends for {term}: {e}")
        # Return empty structure on error for graceful degradation
        return {
            "series": [],
            "latest": 0,
            "average": 0,
            "trend": "unknown",
            "error": str(e)
        }

async def _fetch_google_trends(term: str, window_days: int) -> Dict[str, Any]:
    """
    Internal function to fetch Google Trends data using pytrends.
    """
    try:
        # Run pytrends in executor to avoid blocking
        loop = asyncio.get_event_loop()
        trends_data = await loop.run_in_executor(None, _get_trends_data, term, window_days)
        
        return trends_data
        
    except Exception as e:
        logger.error(f"Error in _fetch_google_trends for {term}: {e}")
        raise TrendsError(f"Failed to fetch trends data: {e}")

def _get_trends_data(term: str, window_days: int) -> Dict[str, Any]:
    """
    Synchronous function to get trends data using pytrends.
    This runs in a separate thread to avoid blocking the async event loop.
    """
    try:
        # Initialize pytrends
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Determine timeframe
        if window_days <= 7:
            timeframe = 'now 7-d'
        elif window_days <= 30:
            timeframe = 'today 1-m'
        elif window_days <= 90:
            timeframe = 'today 3-m'
        else:
            timeframe = 'today 12-m'
        
        # Build payload
        pytrends.build_payload([term], cat=0, timeframe=timeframe, geo='US', gprop='')
        
        # Get interest over time
        interest_df = pytrends.interest_over_time()
        
        if interest_df.empty or term not in interest_df.columns:
            logger.warning(f"No trends data found for term: {term}")
            return {
                "series": [],
                "latest": 0,
                "average": 0,
                "trend": "no_data",
                "peak_value": 0,
                "peak_date": None
            }
        
        # Extract data for the term
        series_data = []
        values = interest_df[term].tolist()
        dates = interest_df.index.tolist()
        
        for date, value in zip(dates, values):
            series_data.append({
                "date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                "value": int(value) if pd.notna(value) else 0
            })
        
        # Calculate metrics
        valid_values = [v for v in values if pd.notna(v)]
        
        if not valid_values:
            return {
                "series": series_data,
                "latest": 0,
                "average": 0,
                "trend": "no_data",
                "peak_value": 0,
                "peak_date": None
            }
        
        latest_value = valid_values[-1] if valid_values else 0
        average_value = sum(valid_values) / len(valid_values)
        peak_value = max(valid_values)
        peak_index = values.index(peak_value)
        peak_date = dates[peak_index].strftime("%Y-%m-%d") if hasattr(dates[peak_index], 'strftime') else str(dates[peak_index])
        
        # Determine trend direction
        trend = _calculate_trend(valid_values)
        
        # Get related queries if available
        related_queries = _get_related_queries(pytrends)
        
        return {
            "series": series_data,
            "latest": int(latest_value),
            "average": round(average_value, 1),
            "trend": trend,
            "peak_value": int(peak_value),
            "peak_date": peak_date,
            "related_queries": related_queries,
            "timeframe": timeframe,
            "total_points": len(series_data)
        }
        
    except Exception as e:
        logger.error(f"Error in _get_trends_data for {term}: {e}")
        raise

def _calculate_trend(values: List[float]) -> str:
    """
    Calculate trend direction from values.
    """
    if len(values) < 2:
        return "insufficient_data"
    
    # Compare recent values (last 25%) with earlier values (first 25%)
    recent_count = max(1, len(values) // 4)
    recent_avg = sum(values[-recent_count:]) / recent_count
    early_avg = sum(values[:recent_count]) / recent_count
    
    # Calculate percentage change
    if early_avg == 0:
        return "unknown"
    
    change_pct = (recent_avg - early_avg) / early_avg
    
    if change_pct > 0.2:  # 20% increase
        return "strongly_increasing"
    elif change_pct > 0.05:  # 5% increase
        return "increasing"
    elif change_pct < -0.2:  # 20% decrease
        return "strongly_decreasing"
    elif change_pct < -0.05:  # 5% decrease
        return "decreasing"
    else:
        return "stable"

def _get_related_queries(pytrends: TrendReq) -> Dict[str, List[str]]:
    """
    Get related queries from pytrends.
    """
    try:
        related_queries = pytrends.related_queries()
        
        result = {
            "top": [],
            "rising": []
        }
        
        if related_queries:
            for term, data in related_queries.items():
                if isinstance(data, dict):
                    if 'top' in data and data['top'] is not None:
                        top_queries = data['top']['query'].head(5).tolist()
                        result['top'] = top_queries
                    
                    if 'rising' in data and data['rising'] is not None:
                        rising_queries = data['rising']['query'].head(5).tolist()
                        result['rising'] = rising_queries
                
                break  # Only process first term
        
        return result
        
    except Exception as e:
        logger.debug(f"Error getting related queries: {e}")
        return {"top": [], "rising": []}

async def get_comparative_trends(
    terms: List[str],
    window_days: int = 30
) -> Dict[str, Any]:
    """
    Get comparative trends data for multiple terms.
    """
    cache_key = f"comparative_trends_{'_'.join(terms)}_{window_days}"
    
    if cache_key in trends_cache:
        logger.info(f"Comparative trends cache hit for {terms}")
        return trends_cache[cache_key]
    
    try:
        async with trends_throttler:
            comparative_data = await _fetch_comparative_trends(terms, window_days)
            
        trends_cache[cache_key] = comparative_data
        logger.info(f"Comparative trends fetched and cached for {terms}")
        
        return comparative_data
        
    except Exception as e:
        logger.error(f"Error fetching comparative trends for {terms}: {e}")
        return {
            "terms": terms,
            "series": [],
            "latest_values": {},
            "error": str(e)
        }

async def _fetch_comparative_trends(terms: List[str], window_days: int) -> Dict[str, Any]:
    """
    Fetch comparative trends data for multiple terms.
    """
    try:
        loop = asyncio.get_event_loop()
        comparative_data = await loop.run_in_executor(None, _get_comparative_trends_data, terms, window_days)
        
        return comparative_data
        
    except Exception as e:
        logger.error(f"Error in _fetch_comparative_trends: {e}")
        raise TrendsError(f"Failed to fetch comparative trends: {e}")

def _get_comparative_trends_data(terms: List[str], window_days: int) -> Dict[str, Any]:
    """
    Get comparative trends data using pytrends.
    """
    try:
        # Limit to 5 terms max (Google Trends limitation)
        terms = terms[:5]
        
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Determine timeframe
        if window_days <= 7:
            timeframe = 'now 7-d'
        elif window_days <= 30:
            timeframe = 'today 1-m'
        elif window_days <= 90:
            timeframe = 'today 3-m'
        else:
            timeframe = 'today 12-m'
        
        # Build payload with multiple terms
        pytrends.build_payload(terms, cat=0, timeframe=timeframe, geo='US', gprop='')
        
        # Get interest over time
        interest_df = pytrends.interest_over_time()
        
        if interest_df.empty:
            return {
                "terms": terms,
                "series": [],
                "latest_values": {},
                "timeframe": timeframe
            }
        
        # Format data
        series_data = []
        latest_values = {}
        
        dates = interest_df.index.tolist()
        
        for date in dates:
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
            date_data = {"date": date_str}
            
            for term in terms:
                if term in interest_df.columns:
                    value = interest_df.loc[date, term]
                    date_data[term] = int(value) if pd.notna(value) else 0
                else:
                    date_data[term] = 0
            
            series_data.append(date_data)
        
        # Get latest values
        for term in terms:
            if term in interest_df.columns:
                latest_values[term] = int(interest_df[term].iloc[-1]) if not interest_df[term].empty else 0
            else:
                latest_values[term] = 0
        
        return {
            "terms": terms,
            "series": series_data,
            "latest_values": latest_values,
            "timeframe": timeframe,
            "total_points": len(series_data)
        }
        
    except Exception as e:
        logger.error(f"Error in _get_comparative_trends_data: {e}")
        raise

# Utility functions
def clear_trends_cache():
    """Clear the Google Trends cache"""
    trends_cache.clear()
    logger.info("Google Trends cache cleared")

def get_cache_stats() -> Dict[str, Any]:
    """Get trends cache statistics"""
    return {
        "cache_size": len(trends_cache),
        "max_size": trends_cache.maxsize,
        "ttl": trends_cache.ttl,
        "hits": getattr(trends_cache, 'hits', 0),
        "misses": getattr(trends_cache, 'misses', 0)
    }

def analyze_trend_momentum(series_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze momentum from trends series data.
    """
    if not series_data:
        return {"momentum": "no_data", "score": 0}
    
    values = [point.get("value", 0) for point in series_data]
    
    if len(values) < 3:
        return {"momentum": "insufficient_data", "score": 0}
    
    # Calculate momentum using recent vs historical comparison
    recent_period = len(values) // 3  # Last third
    recent_avg = sum(values[-recent_period:]) / recent_period
    historical_avg = sum(values[:-recent_period]) / (len(values) - recent_period)
    
    if historical_avg == 0:
        momentum_score = 0
    else:
        momentum_score = (recent_avg - historical_avg) / historical_avg
    
    # Classify momentum
    if momentum_score > 0.5:
        momentum = "very_strong"
    elif momentum_score > 0.2:
        momentum = "strong"
    elif momentum_score > 0.05:
        momentum = "moderate"
    elif momentum_score > -0.05:
        momentum = "neutral"
    elif momentum_score > -0.2:
        momentum = "weak"
    else:
        momentum = "very_weak"
    
    return {
        "momentum": momentum,
        "score": round(momentum_score, 3),
        "recent_average": round(recent_avg, 1),
        "historical_average": round(historical_avg, 1)
    }