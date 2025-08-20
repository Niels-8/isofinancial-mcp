"""
News Headlines data client
Handles Yahoo Finance RSS feed parsing with caching and duplicate detection
"""

import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from cachetools import TTLCache
from asyncio_throttle import Throttler
import logging
import hashlib
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache with 2-hour TTL as per requirements
news_cache = TTLCache(maxsize=1000, ttl=7200)  # 2 hours = 7200 seconds

# Rate limiter for news data (5 requests per second)
news_throttler = Throttler(rate_limit=5, period=1.0)

class NewsError(Exception):
    """Custom exception for news data errors"""
    pass

async def get_news_headlines(
    ticker: str,
    limit: int = 10,
    lookback_days: int = 3
) -> List[Dict[str, Any]]:
    """
    Retrieve recent news headlines with source attribution and duplicate detection.
    
    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of headlines to return (default: 10)
        lookback_days: Number of days to look back for news (default: 3)
    
    Returns:
        List of news dictionaries with published_at, source, title, and url
    """
    # Create cache key
    cache_key = f"news_{ticker}_{limit}_{lookback_days}"
    
    # Check cache first
    if cache_key in news_cache:
        logger.info(f"News headlines cache hit for {ticker}")
        return news_cache[cache_key]
    
    try:
        # Apply rate limiting
        async with news_throttler:
            news_data = await _fetch_news_headlines(ticker, limit, lookback_days)
            
        # Remove duplicates
        news_data = _remove_duplicate_headlines(news_data)
        
        # Cache the results
        news_cache[cache_key] = news_data
        logger.info(f"News headlines fetched and cached for {ticker}: {len(news_data)} articles")
        
        return news_data
        
    except Exception as e:
        logger.error(f"Error fetching news headlines for {ticker}: {e}")
        # Return empty list on error for graceful degradation
        return []

async def _fetch_news_headlines(
    ticker: str,
    limit: int,
    lookback_days: int
) -> List[Dict[str, Any]]:
    """
    Internal function to fetch news headlines from multiple sources.
    """
    all_news = []
    
    # Fetch from Yahoo Finance RSS
    yahoo_news = await _fetch_yahoo_rss_news(ticker, lookback_days)
    if yahoo_news:
        all_news.extend(yahoo_news)
    
    # Fetch from additional sources if needed
    if len(all_news) < limit:
        additional_news = await _fetch_additional_news_sources(ticker, lookback_days)
        all_news.extend(additional_news)
    
    # Sort by publication date (most recent first)
    all_news.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    # Return limited results
    return all_news[:limit]

async def _fetch_yahoo_rss_news(ticker: str, lookback_days: int) -> List[Dict[str, Any]]:
    """
    Fetch news from Yahoo Finance RSS feed.
    """
    try:
        # Yahoo Finance RSS URL for specific ticker
        rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        
        headers = {
            "User-Agent": "IsoFinancial-MCP/1.0 (contact@example.com)",
            "Accept": "application/rss+xml, application/xml, text/xml"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(rss_url) as response:
                if response.status != 200:
                    logger.warning(f"Yahoo RSS returned status {response.status} for {ticker}")
                    return []
                
                rss_content = await response.text()
        
        # Parse RSS feed
        feed = feedparser.parse(rss_content)
        
        if not feed.entries:
            logger.info(f"No RSS entries found for {ticker}")
            return []
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        news_items = []
        
        for entry in feed.entries:
            try:
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    # Try to parse various date formats
                    pub_date = _parse_date_string(entry.published)
                
                # Filter by date
                if pub_date and pub_date < cutoff_date:
                    continue
                
                # Extract news item data
                news_item = {
                    "published_at": pub_date.isoformat() if pub_date else "",
                    "source": "Yahoo Finance",
                    "title": entry.get('title', '').strip(),
                    "url": entry.get('link', ''),
                    "summary": entry.get('summary', '').strip(),
                    "ticker": ticker.upper()
                }
                
                # Only add if we have essential fields
                if news_item["title"] and news_item["url"]:
                    news_items.append(news_item)
                    
            except Exception as e:
                logger.debug(f"Error parsing RSS entry: {e}")
                continue
        
        return news_items
        
    except Exception as e:
        logger.error(f"Error fetching Yahoo RSS news for {ticker}: {e}")
        return []

async def _fetch_additional_news_sources(ticker: str, lookback_days: int) -> List[Dict[str, Any]]:
    """
    Fetch news from additional sources as fallback.
    """
    additional_news = []
    
    # Try Google News RSS
    google_news = await _fetch_google_news_rss(ticker, lookback_days)
    if google_news:
        additional_news.extend(google_news)
    
    # Try Alpha Vantage News (if API key available)
    # av_news = await _fetch_alpha_vantage_news(ticker, lookback_days)
    # if av_news:
    #     additional_news.extend(av_news)
    
    return additional_news

async def _fetch_google_news_rss(ticker: str, lookback_days: int) -> List[Dict[str, Any]]:
    """
    Fetch news from Google News RSS as alternative source.
    """
    try:
        # Google News RSS URL for ticker search
        search_query = f"{ticker} stock"
        rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=US&ceid=US:en"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(rss_url) as response:
                if response.status != 200:
                    return []
                
                rss_content = await response.text()
        
        # Parse RSS feed
        feed = feedparser.parse(rss_content)
        
        if not feed.entries:
            return []
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        news_items = []
        
        for entry in feed.entries:
            try:
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    pub_date = _parse_date_string(entry.published)
                
                # Filter by date
                if pub_date and pub_date < cutoff_date:
                    continue
                
                # Check if the article is relevant to the ticker
                title = entry.get('title', '').lower()
                summary = entry.get('summary', '').lower()
                
                if ticker.lower() not in title and ticker.lower() not in summary:
                    continue
                
                # Extract source from Google News format
                source = "Google News"
                if hasattr(entry, 'source') and entry.source:
                    source = entry.source.get('title', 'Google News')
                
                news_item = {
                    "published_at": pub_date.isoformat() if pub_date else "",
                    "source": source,
                    "title": entry.get('title', '').strip(),
                    "url": entry.get('link', ''),
                    "summary": entry.get('summary', '').strip(),
                    "ticker": ticker.upper()
                }
                
                if news_item["title"] and news_item["url"]:
                    news_items.append(news_item)
                    
            except Exception as e:
                logger.debug(f"Error parsing Google News entry: {e}")
                continue
        
        return news_items
        
    except Exception as e:
        logger.error(f"Error fetching Google News for {ticker}: {e}")
        return []

def _parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse various date string formats.
    """
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 2822
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 with timezone
        "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601
        "%Y-%m-%dT%H:%M:%SZ",        # ISO 8601 UTC
        "%Y-%m-%d %H:%M:%S",         # Simple format
        "%d %b %Y %H:%M:%S",         # Alternative format
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, try to extract date components with regex
    try:
        # Look for patterns like "Mon, 15 Jan 2024 10:30:00"
        date_match = re.search(r'(\d{1,2})\s+(\w{3})\s+(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})', date_str)
        if date_match:
            day, month_str, year, hour, minute, second = date_match.groups()
            
            # Convert month name to number
            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            
            month = months.get(month_str.lower())
            if month:
                return datetime(int(year), month, int(day), int(hour), int(minute), int(second))
    
    except Exception:
        pass
    
    logger.debug(f"Could not parse date string: {date_str}")
    return None

def _remove_duplicate_headlines(news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate headlines based on title similarity and URL.
    """
    if not news_items:
        return []
    
    seen_urls = set()
    seen_titles = set()
    unique_items = []
    
    for item in news_items:
        url = item.get("url", "")
        title = item.get("title", "").lower().strip()
        
        # Create a hash of the title for similarity detection
        title_hash = hashlib.md5(title.encode()).hexdigest()
        
        # Skip if we've seen this URL or very similar title
        if url in seen_urls or title_hash in seen_titles:
            continue
        
        # Check for similar titles (simple approach)
        is_duplicate = False
        for existing_title in seen_titles:
            if _titles_are_similar(title, existing_title):
                is_duplicate = True
                break
        
        if not is_duplicate:
            seen_urls.add(url)
            seen_titles.add(title_hash)
            unique_items.append(item)
    
    return unique_items

def _titles_are_similar(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """
    Check if two titles are similar using simple word overlap.
    """
    if not title1 or not title2:
        return False
    
    # Simple similarity check based on word overlap
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())
    
    if not words1 or not words2:
        return False
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    similarity = len(intersection) / len(union) if union else 0
    return similarity >= threshold

# Utility functions
def clear_news_cache():
    """Clear the news headlines cache"""
    news_cache.clear()
    logger.info("News headlines cache cleared")

def get_cache_stats() -> Dict[str, Any]:
    """Get news cache statistics"""
    return {
        "cache_size": len(news_cache),
        "max_size": news_cache.maxsize,
        "ttl": news_cache.ttl,
        "hits": getattr(news_cache, 'hits', 0),
        "misses": getattr(news_cache, 'misses', 0)
    }

def filter_news_by_keywords(
    news_items: List[Dict[str, Any]],
    keywords: List[str],
    exclude_keywords: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter news items by including/excluding specific keywords.
    """
    if not news_items:
        return []
    
    if exclude_keywords is None:
        exclude_keywords = []
    
    filtered_items = []
    
    for item in news_items:
        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        content = f"{title} {summary}"
        
        # Check if any include keywords are present
        has_include_keyword = not keywords or any(keyword.lower() in content for keyword in keywords)
        
        # Check if any exclude keywords are present
        has_exclude_keyword = any(keyword.lower() in content for keyword in exclude_keywords)
        
        if has_include_keyword and not has_exclude_keyword:
            filtered_items.append(item)
    
    return filtered_items

def get_news_sentiment_keywords() -> Dict[str, List[str]]:
    """
    Get predefined keyword lists for sentiment analysis.
    """
    return {
        "positive": [
            "beats", "exceeds", "strong", "growth", "profit", "revenue", "upgrade",
            "bullish", "rally", "surge", "gains", "positive", "outperform", "buy"
        ],
        "negative": [
            "misses", "falls", "decline", "loss", "downgrade", "bearish", "crash",
            "plunge", "drops", "negative", "underperform", "sell", "warning"
        ],
        "neutral": [
            "announces", "reports", "updates", "conference", "meeting", "guidance",
            "outlook", "forecast", "estimates", "analyst", "coverage"
        ]
    }