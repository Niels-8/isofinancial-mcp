"""
Earnings Source Manager with multi-source fallback and data fusion.

This module consolidates all earnings-related functionality including:
- Individual data source implementations (Nasdaq, Alpha Vantage)
- Data merging and deduplication utilities
- Earnings estimation logic
- Multi-source manager with fallback
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re

from ..reliability.data_manager import DataManager
from ..reliability.error_handler import ErrorHandler
from ..reliability.models import DataResult

logger = logging.getLogger(__name__)


# ============================================================================
# Utility Functions (from earnings_sources.py)
# ============================================================================

def merge_earnings_data(
    earnings_lists: List[List[Dict[str, Any]]],
    prioritize_eps: bool = True
) -> List[Dict[str, Any]]:
    """
    Merge and deduplicate earnings data from multiple sources.
    
    Args:
        earnings_lists: List of earnings data lists from different sources
        prioritize_eps: If True, prefer records with EPS estimates
        
    Returns:
        Merged and deduplicated list of earnings records
    """
    # Flatten all earnings into a single list
    all_earnings = []
    for earnings_list in earnings_lists:
        if earnings_list:
            all_earnings.extend(earnings_list)
    
    if not all_earnings:
        return []
    
    # Group by date for deduplication
    earnings_by_date = {}
    
    for earning in all_earnings:
        date = earning.get('date', '')
        if not date:
            continue
        
        # Normalize date format for comparison
        normalized_date = _normalize_date(date)
        if not normalized_date:
            continue
        
        # If date not seen yet, add it
        if normalized_date not in earnings_by_date:
            earnings_by_date[normalized_date] = earning
        else:
            # Date already exists - merge or replace based on quality
            existing = earnings_by_date[normalized_date]
            
            if prioritize_eps:
                # Prefer record with EPS estimate
                if earning.get('eps_estimate') is not None and existing.get('eps_estimate') is None:
                    earnings_by_date[normalized_date] = earning
                elif earning.get('eps_estimate') is not None and existing.get('eps_estimate') is not None:
                    # Both have EPS - merge fields, preferring non-None values
                    earnings_by_date[normalized_date] = _merge_records(existing, earning)
                elif existing.get('eps_estimate') is None and earning.get('eps_estimate') is None:
                    # Neither has EPS - merge fields
                    earnings_by_date[normalized_date] = _merge_records(existing, earning)
                # else: existing has EPS and new doesn't, keep existing
            else:
                # Just merge fields
                earnings_by_date[normalized_date] = _merge_records(existing, earning)
    
    # Convert back to list and sort by date (most recent first)
    merged_earnings = list(earnings_by_date.values())
    merged_earnings.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    logger.info(f"Merged {len(all_earnings)} records into {len(merged_earnings)} unique earnings dates")
    return merged_earnings


def _normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize date string to YYYY-MM-DD format.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Normalized date string or None
    """
    if not date_str:
        return None
    
    # Try different date formats
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%b %d, %Y",
        "%B %d, %Y"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # If no format matches, return original
    logger.debug(f"Could not normalize date: {date_str}")
    return date_str


def _merge_records(record1: Dict[str, Any], record2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two earnings records, preferring non-None values.
    
    Args:
        record1: First earnings record
        record2: Second earnings record
        
    Returns:
        Merged earnings record
    """
    merged = record1.copy()
    
    # For each field, prefer non-None value
    for key, value in record2.items():
        if value is not None and (key not in merged or merged[key] is None):
            merged[key] = value
    
    # Track sources if available
    sources = set()
    if record1.get('source'):
        sources.add(record1['source'])
    if record2.get('source'):
        sources.add(record2['source'])
    
    if sources:
        merged['sources'] = list(sources)
    
    return merged


def estimate_next_earnings(
    ticker: str,
    historical_data: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Estimate next earnings date based on quarter patterns.
    
    Earnings are typically reported 45 days after quarter end:
    - Q1 (Jan-Mar): ~May 15
    - Q2 (Apr-Jun): ~Aug 15
    - Q3 (Jul-Sep): ~Nov 15
    - Q4 (Oct-Dec): ~Feb 15
    
    Args:
        ticker: Stock ticker symbol
        historical_data: Optional historical earnings data for pattern analysis
        
    Returns:
        Estimated earnings record or None
    """
    today = datetime.now().date()
    
    # If we have historical data, try to find pattern
    if historical_data and len(historical_data) >= 2:
        # Sort by date
        sorted_data = sorted(
            [e for e in historical_data if e.get('date')],
            key=lambda x: x['date']
        )
        
        if len(sorted_data) >= 2:
            # Calculate average interval between earnings
            intervals = []
            for i in range(len(sorted_data) - 1):
                try:
                    date1 = datetime.strptime(_normalize_date(sorted_data[i]['date']), "%Y-%m-%d").date()
                    date2 = datetime.strptime(_normalize_date(sorted_data[i + 1]['date']), "%Y-%m-%d").date()
                    interval = (date2 - date1).days
                    if 60 <= interval <= 120:  # Reasonable quarterly interval
                        intervals.append(interval)
                except (ValueError, TypeError):
                    continue
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                
                # Get most recent earnings date
                try:
                    last_date_str = _normalize_date(sorted_data[-1]['date'])
                    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                    
                    # Estimate next date
                    estimated_date = last_date + timedelta(days=int(avg_interval))
                    
                    # If estimated date is in the past, add another interval
                    while estimated_date < today:
                        estimated_date += timedelta(days=int(avg_interval))
                    
                    logger.info(f"Estimated next earnings for {ticker} based on historical pattern: {estimated_date}")
                    
                    return {
                        "date": estimated_date.strftime("%Y-%m-%d"),
                        "period": "Estimated",
                        "eps_estimate": None,
                        "eps_actual": None,
                        "eps_surprise": None,
                        "surprise_percentage": None,
                        "timing": "N/A",
                        "revenue_estimate": None,
                        "revenue_actual": None,
                        "source": "estimated",
                        "estimated": True
                    }
                except (ValueError, TypeError) as e:
                    logger.debug(f"Error calculating historical pattern for {ticker}: {e}")
    
    # Fallback: Use standard quarterly pattern
    # Determine current quarter and estimate next earnings
    current_month = today.month
    current_year = today.year
    
    # Quarter end dates and typical earnings dates (45 days after quarter end)
    quarters = [
        (3, 31, 5, 15),   # Q1: Mar 31 -> May 15
        (6, 30, 8, 15),   # Q2: Jun 30 -> Aug 15
        (9, 30, 11, 15),  # Q3: Sep 30 -> Nov 15
        (12, 31, 2, 15),  # Q4: Dec 31 -> Feb 15 (next year)
    ]
    
    # Find next earnings date
    for q_end_month, q_end_day, e_month, e_day in quarters:
        # Calculate earnings date
        earnings_year = current_year
        if e_month < q_end_month:  # Earnings in next year (Q4 case)
            earnings_year += 1
        
        earnings_date = datetime(earnings_year, e_month, e_day).date()
        
        # If this earnings date is in the future, use it
        if earnings_date > today:
            logger.info(f"Estimated next earnings for {ticker} using quarterly pattern: {earnings_date}")
            
            return {
                "date": earnings_date.strftime("%Y-%m-%d"),
                "period": f"Q{quarters.index((q_end_month, q_end_day, e_month, e_day)) + 1} {earnings_year}",
                "eps_estimate": None,
                "eps_actual": None,
                "eps_surprise": None,
                "surprise_percentage": None,
                "timing": "N/A",
                "revenue_estimate": None,
                "revenue_actual": None,
                "source": "estimated",
                "estimated": True
            }
    
    # If we get here, all quarters this year have passed, use Q1 next year
    next_year = current_year + 1
    estimated_date = datetime(next_year, 2, 15).date()
    
    logger.info(f"Estimated next earnings for {ticker} for next year: {estimated_date}")
    
    return {
        "date": estimated_date.strftime("%Y-%m-%d"),
        "period": f"Q4 {current_year}",
        "eps_estimate": None,
        "eps_actual": None,
        "eps_surprise": None,
        "surprise_percentage": None,
        "timing": "N/A",
        "revenue_estimate": None,
        "revenue_actual": None,
        "source": "estimated",
        "estimated": True
    }


# ============================================================================
# Data Source Classes (from earnings_sources.py)
# ============================================================================

class NasdaqEarnings:
    """
    Nasdaq earnings data source.
    """
    
    def __init__(self):
        self.name = "nasdaq"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json"
        }
    
    async def fetch_earnings(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch earnings data from Nasdaq API.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of earnings dictionaries
        """
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # Nasdaq earnings API endpoint
                url = f"https://api.nasdaq.com/api/calendar/earnings?date=2024-01-01&date=2024-12-31"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Nasdaq API returned status {response.status} for {ticker}")
                        return []
                    
                    data = await response.json()
            
            # Parse Nasdaq earnings data with improved error handling
            earnings_data = []
            
            # Safely access nested data structure
            if not isinstance(data, dict):
                logger.warning(f"Nasdaq API returned non-dict response for {ticker}: {type(data)}")
                return []
            
            if 'data' not in data:
                logger.warning(f"Nasdaq API missing 'data' key for {ticker}. Keys: {list(data.keys())}")
                return []
            
            data_section = data['data']
            if not isinstance(data_section, dict):
                logger.warning(f"Nasdaq API 'data' is not a dict for {ticker}: {type(data_section)}")
                return []
            
            if 'rows' not in data_section:
                logger.warning(f"Nasdaq API missing 'rows' key for {ticker}. Keys: {list(data_section.keys())}")
                return []
            
            rows = data_section['rows']
            
            # Ensure rows is iterable and not None
            if rows is None:
                logger.warning(f"Nasdaq API returned None for rows for {ticker}")
                return []
            
            if not hasattr(rows, '__iter__') or isinstance(rows, str):
                logger.warning(f"Nasdaq API returned non-iterable rows for {ticker}: {type(rows)}")
                return []
            
            # Process each row
            for row in rows:
                if not isinstance(row, dict):
                    logger.debug(f"Skipping non-dict row for {ticker}: {type(row)}")
                    continue
                
                if row.get('symbol', '').upper() == ticker.upper():
                    earnings_record = self._format_earnings(row)
                    if earnings_record:
                        earnings_data.append(earnings_record)
            
            logger.info(f"Nasdaq fetched {len(earnings_data)} earnings records for {ticker}")
            return earnings_data
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching Nasdaq earnings for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching Nasdaq earnings for {ticker}: {e}")
            raise
    
    def _format_earnings(self, row_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Format Nasdaq earnings data into standardized structure.
        
        Args:
            row_data: Raw row data from Nasdaq API
            
        Returns:
            Formatted earnings dictionary or None
        """
        try:
            return {
                "date": row_data.get('date', ''),
                "period": row_data.get('fiscalQuarterEnding', ''),
                "eps_estimate": self._safe_float(row_data.get('eps_estimate')),
                "eps_actual": self._safe_float(row_data.get('eps')),
                "eps_surprise": self._safe_float(row_data.get('surprise')),
                "surprise_percentage": self._safe_float(row_data.get('surprisePercentage')),
                "timing": row_data.get('time', 'N/A'),
                "revenue_estimate": self._safe_float(row_data.get('revenueEstimate')),
                "revenue_actual": self._safe_float(row_data.get('revenue')),
                "source": "nasdaq"
            }
        except Exception as e:
            logger.debug(f"Error formatting Nasdaq earnings: {e}")
            return None
    
    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """
        Safely convert value to float.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None
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


class AlphaVantageEarnings:
    """
    Alpha Vantage earnings data source.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Alpha Vantage earnings source.
        
        Args:
            api_key: Alpha Vantage API key (from environment if None)
        """
        import os
        self.name = "alpha_vantage"
        self.api_key = api_key or os.getenv('ALPHA_VANTAGE_KEY')
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    async def fetch_earnings(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch earnings data from Alpha Vantage API.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of earnings dictionaries
        """
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured, skipping")
            raise ValueError("Alpha Vantage API key not configured")
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # Alpha Vantage earnings endpoint
                url = (
                    f"https://www.alphavantage.co/query"
                    f"?function=EARNINGS"
                    f"&symbol={ticker}"
                    f"&apikey={self.api_key}"
                )
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Alpha Vantage returned status {response.status} for {ticker}")
                        raise aiohttp.ClientError(f"HTTP {response.status}")
                    
                    data = await response.json()
            
            # Parse Alpha Vantage earnings data
            earnings_data = []
            
            if not isinstance(data, dict):
                logger.warning(f"Alpha Vantage returned non-dict response for {ticker}")
                return []
            
            # Check for API error messages
            if 'Error Message' in data:
                logger.warning(f"Alpha Vantage error for {ticker}: {data['Error Message']}")
                raise ValueError(data['Error Message'])
            
            if 'Note' in data:
                logger.warning(f"Alpha Vantage rate limit for {ticker}: {data['Note']}")
                raise ValueError("Rate limit exceeded")
            
            # Alpha Vantage returns quarterly and annual earnings
            quarterly_earnings = data.get('quarterlyEarnings', [])
            
            if not isinstance(quarterly_earnings, list):
                logger.warning(f"Alpha Vantage quarterlyEarnings not a list for {ticker}")
                return []
            
            for earning in quarterly_earnings:
                if not isinstance(earning, dict):
                    continue
                
                earnings_record = self._format_earnings(earning)
                if earnings_record:
                    earnings_data.append(earnings_record)
            
            logger.info(f"Alpha Vantage fetched {len(earnings_data)} earnings records for {ticker}")
            return earnings_data
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching Alpha Vantage earnings for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage earnings for {ticker}: {e}")
            raise
    
    def _format_earnings(self, earning_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Format Alpha Vantage earnings data into standardized structure.
        
        Args:
            earning_data: Raw earnings data from Alpha Vantage
            
        Returns:
            Formatted earnings dictionary or None
        """
        try:
            # Alpha Vantage uses 'reportedDate' and 'fiscalDateEnding'
            reported_date = earning_data.get('reportedDate', '')
            fiscal_date = earning_data.get('fiscalDateEnding', '')
            
            # Get EPS values
            reported_eps = self._safe_float(earning_data.get('reportedEPS'))
            estimated_eps = self._safe_float(earning_data.get('estimatedEPS'))
            
            # Calculate surprise
            eps_surprise = None
            surprise_percentage = None
            if reported_eps is not None and estimated_eps is not None:
                eps_surprise = reported_eps - estimated_eps
                if estimated_eps != 0:
                    surprise_percentage = (eps_surprise / estimated_eps) * 100
            
            return {
                "date": reported_date,
                "period": fiscal_date,
                "eps_estimate": estimated_eps,
                "eps_actual": reported_eps,
                "eps_surprise": eps_surprise,
                "surprise_percentage": surprise_percentage,
                "timing": "N/A",
                "revenue_estimate": None,
                "revenue_actual": None,
                "source": "alpha_vantage"
            }
        except Exception as e:
            logger.debug(f"Error formatting Alpha Vantage earnings: {e}")
            return None
    
    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """
        Safely convert value to float.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None
        """
        if value is None or value == 'None':
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# ============================================================================
# Earnings Source Manager (original content)
# ============================================================================


class EarningsSourceManager:
    """
    Manages multiple earnings data sources with automatic fallback and fusion.
    """
    
    def __init__(
        self,
        data_manager: Optional[DataManager] = None,
        alpha_vantage_key: Optional[str] = None,
        error_handler: Optional[ErrorHandler] = None
    ):
        """
        Initialize earnings source manager.
        
        Args:
            data_manager: Data manager for caching and health monitoring
            alpha_vantage_key: Optional Alpha Vantage API key
            error_handler: Error handler instance for error classification
        """
        self.data_manager = data_manager or DataManager()
        self.error_handler = error_handler or ErrorHandler()
        
        # Initialize sources in priority order
        self.sources = [
            ("nasdaq", NasdaqEarnings()),
            ("alpha_vantage", AlphaVantageEarnings(api_key=alpha_vantage_key))
        ]
        
        logger.info(f"Initialized EarningsSourceManager with {len(self.sources)} sources")
    
    async def fetch_earnings(
        self,
        ticker: str,
        use_estimation: bool = True,
        require_future_date: bool = True
    ) -> DataResult:
        """
        Fetch earnings data with multi-source fusion and fallback.
        
        Strategy:
        1. Fetch from all sources in parallel
        2. Merge and deduplicate results
        3. If no data, use estimation fallback
        4. Validate at least one future date exists
        
        Args:
            ticker: Stock ticker symbol
            use_estimation: If True, estimate earnings if no data available
            require_future_date: If True, ensure at least one future date exists
            
        Returns:
            DataResult with earnings data
        """
        cache_key = f"earnings_{ticker}"
        
        # Check cache first
        cached_data = await self.data_manager.cache_layer.get(cache_key, allow_stale=False)
        if cached_data is not None and not cached_data.is_stale:
            cache_age = int((datetime.now() - cached_data.cached_at).total_seconds())
            logger.info(f"Cache hit for earnings {ticker} (age: {cache_age}s)")
            
            return DataResult(
                data=cached_data.data,
                source_used=cached_data.source,
                is_cached=True,
                cache_age_seconds=cache_age,
                is_stale=False,
                attempted_sources=[],
                successful_sources=[cached_data.source],
                failed_sources=[],
                errors=[],
                timestamp=datetime.now(),
                partial_data=False,
                last_successful_update=cached_data.cached_at
            )
        
        # Fetch from all sources in parallel
        tasks = []
        source_names = []
        
        for source_name, source_obj in self.sources:
            tasks.append(self._fetch_from_source(source_name, source_obj, ticker))
            source_names.append(source_name)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results and errors
        earnings_lists = []
        errors = []
        successful_sources = []
        
        for source_name, result in zip(source_names, results):
            if isinstance(result, Exception):
                error_info = self.error_handler.classify_error(
                    source=f"earnings_{source_name}",
                    error=result,
                    context=f"earnings fetch for {ticker}"
                )
                errors.append(error_info)
                logger.warning(f"Failed to fetch from {source_name}: {result}")
            elif result:
                earnings_lists.append(result)
                successful_sources.append(source_name)
                logger.info(f"Successfully fetched {len(result)} records from {source_name}")
        
        # Merge data from all successful sources
        merged_earnings = merge_earnings_data(earnings_lists, prioritize_eps=True)
        
        # If no data and estimation enabled, estimate next earnings
        if not merged_earnings and use_estimation:
            logger.info(f"No earnings data found for {ticker}, using estimation")
            estimated = estimate_next_earnings(ticker)
            if estimated:
                merged_earnings = [estimated]
                successful_sources.append("estimated")
        
        # Validate future date requirement
        if require_future_date and merged_earnings:
            has_future_date = self._has_future_date(merged_earnings)
            
            if not has_future_date:
                logger.warning(f"No future earnings date found for {ticker}")
                
                # Try to add estimated future date
                if use_estimation:
                    estimated = estimate_next_earnings(ticker, merged_earnings)
                    if estimated:
                        merged_earnings.append(estimated)
                        logger.info(f"Added estimated future earnings date for {ticker}")
        
        # Determine source used
        if successful_sources:
            source_used = "+".join(successful_sources)
        else:
            source_used = "none"
        
        # Cache the result if we have data
        if merged_earnings:
            await self.data_manager.cache_layer.set(
                key=cache_key,
                data=merged_earnings,
                source=source_used,
                ttl_memory=3600,  # 1 hour
                ttl_disk=86400    # 24 hours
            )
        
        # Check if we have partial data (some sources failed)
        partial_data = len(successful_sources) > 0 and len(errors) > 0
        failed_sources = [err.source for err in errors]
        
        # Determine last successful update
        last_update = datetime.now() if successful_sources else None
        
        return DataResult(
            data=merged_earnings,
            source_used=source_used,
            is_cached=False,
            cache_age_seconds=None,
            is_stale=False,
            attempted_sources=source_names,
            successful_sources=successful_sources,
            failed_sources=failed_sources,
            errors=errors,
            timestamp=datetime.now(),
            partial_data=partial_data,
            last_successful_update=last_update
        )
    
    async def _fetch_from_source(
        self,
        source_name: str,
        source_obj: Any,
        ticker: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch earnings from a single source with timing.
        
        Args:
            source_name: Name of the source
            source_obj: Source object with fetch_earnings method
            ticker: Stock ticker symbol
            
        Returns:
            List of earnings records
        """
        start_time = datetime.now()
        
        try:
            earnings = await source_obj.fetch_earnings(ticker)
            
            # Record success
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.data_manager.health_monitor.record_request(
                source=f"earnings_{source_name}",
                success=True,
                latency_ms=latency_ms
            )
            
            return earnings
            
        except Exception as e:
            # Record failure
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.data_manager.health_monitor.record_request(
                source=f"earnings_{source_name}",
                success=False,
                latency_ms=latency_ms,
                error_type=type(e).__name__
            )
            
            raise
    
    def _has_future_date(self, earnings_data: List[Dict[str, Any]]) -> bool:
        """
        Check if earnings data contains at least one future date.
        
        Args:
            earnings_data: List of earnings records
            
        Returns:
            True if at least one future date exists
        """
        today = datetime.now().date()
        
        for earning in earnings_data:
            date_str = earning.get('date', '')
            if not date_str:
                continue
            
            try:
                # Try to parse date
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        earning_date = datetime.strptime(date_str, fmt).date()
                        if earning_date > today:
                            return True
                        break
                    except ValueError:
                        continue
            except Exception as e:
                logger.debug(f"Error parsing date {date_str}: {e}")
                continue
        
        return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of all earnings sources.
        
        Returns:
            Dictionary with health status for each source
        """
        status = {}
        
        for source_name, _ in self.sources:
            source_key = f"earnings_{source_name}"
            health = self.data_manager.health_monitor.get_health_status(source_key)
            
            status[source_name] = {
                "success_rate": health.success_rate,
                "avg_latency_ms": health.avg_latency_ms,
                "total_requests": health.total_requests,
                "status": health.status,
                "last_success": health.last_success.isoformat() if health.last_success else None
            }
        
        return status
