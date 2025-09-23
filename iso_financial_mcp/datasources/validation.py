"""
Data validation utilities for datasources
Provides common validation functions for ticker symbols, dates, and other inputs
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize ticker symbol.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Normalized ticker symbol (uppercase)
        
    Raises:
        ValidationError: If ticker is invalid
    """
    if not ticker or not isinstance(ticker, str):
        raise ValidationError("Ticker must be a non-empty string")
    
    # Remove whitespace and convert to uppercase
    ticker = ticker.strip().upper()
    
    # Basic ticker format validation
    # Allow alphanumeric characters, dots, and hyphens (for various markets)
    if not re.match(r'^[A-Z0-9.-]{1,10}$', ticker):
        raise ValidationError(f"Invalid ticker format: {ticker}")
    
    # Check for common invalid patterns
    if ticker in ['', 'NULL', 'NONE', 'N/A']:
        raise ValidationError(f"Invalid ticker value: {ticker}")
    
    return ticker

def validate_date_string(date_str: str, name: str = "date") -> str:
    """
    Validate date string format (YYYY-MM-DD).
    
    Args:
        date_str: Date string to validate
        name: Name of the date field for error messages
        
    Returns:
        Validated date string
        
    Raises:
        ValidationError: If date format is invalid
    """
    if not date_str or not isinstance(date_str, str):
        raise ValidationError(f"{name} must be a non-empty string")
    
    # Validate date format
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"Invalid {name} format. Expected YYYY-MM-DD, got: {date_str}")
    
    # Check if date is reasonable (not too far in past or future)
    min_date = datetime(1990, 1, 1)  # Market data typically not available before 1990
    max_date = datetime.now() + timedelta(days=730)  # Allow up to 2 years in future
    
    if parsed_date < min_date:
        raise ValidationError(f"{name} is too far in the past: {date_str}")
    
    if parsed_date > max_date:
        raise ValidationError(f"{name} is too far in the future: {date_str}")
    
    return date_str

def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Validate date range with start and end dates.
    
    Args:
        start_date: Start date string (YYYY-MM-DD) or None
        end_date: End date string (YYYY-MM-DD) or None
        
    Returns:
        Tuple of validated (start_date, end_date)
        
    Raises:
        ValidationError: If date range is invalid
    """
    # Validate individual dates if provided
    if start_date:
        start_date = validate_date_string(start_date, "start_date")
    
    if end_date:
        end_date = validate_date_string(end_date, "end_date")
    
    # Check date range logic
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        if start_dt > end_dt:
            raise ValidationError(f"start_date ({start_date}) must be before end_date ({end_date})")
        
        # Check if range is reasonable (not more than 10 years)
        if (end_dt - start_dt).days > 3650:
            raise ValidationError(f"Date range too large: {(end_dt - start_dt).days} days (max: 3650)")
    
    return start_date, end_date

def validate_positive_integer(value: int, name: str, min_value: int = 1, max_value: int = 10000) -> int:
    """
    Validate positive integer within reasonable bounds.
    
    Args:
        value: Integer value to validate
        name: Name of the field for error messages
        min_value: Minimum allowed value (default: 1)
        max_value: Maximum allowed value (default: 10000)
        
    Returns:
        Validated integer value
        
    Raises:
        ValidationError: If value is invalid
    """
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer, got: {type(value).__name__}")
    
    if value < min_value:
        raise ValidationError(f"{name} must be at least {min_value}, got: {value}")
    
    if value > max_value:
        raise ValidationError(f"{name} must be at most {max_value}, got: {value}")
    
    return value

def validate_form_types(form_types: List[str]) -> List[str]:
    """
    Validate SEC form types list.
    
    Args:
        form_types: List of SEC form type strings
        
    Returns:
        Validated list of form types
        
    Raises:
        ValidationError: If form types are invalid
    """
    if not form_types or not isinstance(form_types, list):
        raise ValidationError("form_types must be a non-empty list")
    
    if len(form_types) > 20:
        raise ValidationError(f"Too many form types specified: {len(form_types)} (max: 20)")
    
    # Known valid SEC form types
    valid_forms = {
        '8-K', '10-K', '10-Q', '20-F', '6-K', 'S-1', 'S-3', 'S-4', 'S-8',
        '424B1', '424B2', '424B3', '424B4', '424B5', '424B', 'DEF 14A',
        'PREM14A', 'SC 13D', 'SC 13G', '13F-HR', '11-K', 'NPORT-P', 'N-CSR'
    }
    
    validated_forms = []
    for form in form_types:
        if not isinstance(form, str):
            raise ValidationError(f"Form type must be a string, got: {type(form).__name__}")
        
        form = form.strip().upper()
        if not form:
            continue
        
        # Allow some flexibility for form variations
        if form not in valid_forms and not re.match(r'^[A-Z0-9-/ ]{1,20}$', form):
            logger.warning(f"Unknown SEC form type: {form}")
        
        validated_forms.append(form)
    
    if not validated_forms:
        raise ValidationError("No valid form types provided")
    
    return validated_forms

def validate_period_string(period: str) -> str:
    """
    Validate yfinance period string.
    
    Args:
        period: Period string (e.g., '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        
    Returns:
        Validated period string
        
    Raises:
        ValidationError: If period is invalid
    """
    if not period or not isinstance(period, str):
        raise ValidationError("Period must be a non-empty string")
    
    period = period.strip().lower()
    
    # Valid yfinance periods
    valid_periods = {
        '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
    }
    
    if period not in valid_periods:
        raise ValidationError(f"Invalid period: {period}. Valid options: {', '.join(sorted(valid_periods))}")
    
    return period

def validate_interval_string(interval: str) -> str:
    """
    Validate yfinance interval string.
    
    Args:
        interval: Interval string (e.g., '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
        
    Returns:
        Validated interval string
        
    Raises:
        ValidationError: If interval is invalid
    """
    if not interval or not isinstance(interval, str):
        raise ValidationError("Interval must be a non-empty string")
    
    interval = interval.strip().lower()
    
    # Valid yfinance intervals
    valid_intervals = {
        '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
    }
    
    if interval not in valid_intervals:
        raise ValidationError(f"Invalid interval: {interval}. Valid options: {', '.join(sorted(valid_intervals))}")
    
    return interval

def validate_frequency(freq: str) -> str:
    """
    Validate frequency string for financial data.
    
    Args:
        freq: Frequency string ('yearly' or 'quarterly')
        
    Returns:
        Validated frequency string
        
    Raises:
        ValidationError: If frequency is invalid
    """
    if not freq or not isinstance(freq, str):
        raise ValidationError("Frequency must be a non-empty string")
    
    freq = freq.strip().lower()
    
    if freq not in ['yearly', 'quarterly']:
        raise ValidationError(f"Invalid frequency: {freq}. Valid options: 'yearly', 'quarterly'")
    
    return freq

def sanitize_string_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing dangerous characters and limiting length.
    
    Args:
        input_str: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If input is invalid
    """
    if not isinstance(input_str, str):
        raise ValidationError(f"Input must be a string, got: {type(input_str).__name__}")
    
    # Remove control characters and limit length
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)
    sanitized = sanitized.strip()
    
    if len(sanitized) > max_length:
        raise ValidationError(f"Input too long: {len(sanitized)} characters (max: {max_length})")
    
    return sanitized

