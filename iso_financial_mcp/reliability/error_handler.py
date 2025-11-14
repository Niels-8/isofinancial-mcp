"""
Error handler for classifying and managing errors.
"""

import logging
from typing import Optional
from datetime import datetime

from .models import ErrorInfo

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Handles error classification and generates actionable error messages.
    """
    
    def classify_error(
        self,
        source: str,
        error: Exception,
        context: Optional[str] = None
    ) -> ErrorInfo:
        """
        Classify an error and determine appropriate action.
        
        Args:
            source: Source name where error occurred
            error: Exception that occurred
            context: Optional context about the operation
            
        Returns:
            ErrorInfo object with classification and suggested action
        """
        error_message = str(error)
        error_class = type(error).__name__
        
        # Log the error for debugging
        logger.debug(
            f"Classifying error from {source}: {error_class} - {error_message}"
        )
        
        # Check for HTTP status code errors
        if hasattr(error, 'status') or hasattr(error, 'status_code'):
            status_code = getattr(error, 'status', None) or getattr(error, 'status_code', None)
            return self._classify_http_error(source, status_code, error_message, context)
        
        # Check for specific error patterns in message
        error_lower = error_message.lower()
        
        # Rate limiting errors
        if any(pattern in error_lower for pattern in ['429', 'rate limit', 'too many requests']):
            return ErrorInfo(
                source=source,
                error_type="rate_limit",
                error_message=f"Rate limit exceeded: {error_message}",
                is_temporary=True,
                suggested_action="Retry with exponential backoff (10s, 20s, 40s). Consider using alternative source.",
                timestamp=datetime.now()
            )
        
        # Timeout errors
        if any(pattern in error_lower for pattern in ['timeout', 'timed out', 'time out']):
            return ErrorInfo(
                source=source,
                error_type="timeout",
                error_message=f"Request timeout: {error_message}",
                is_temporary=True,
                suggested_action="Retry with increased timeout. Check network connectivity.",
                timestamp=datetime.now()
            )
        
        # Connection errors
        if any(pattern in error_lower for pattern in ['connection', 'connect', 'network']):
            return ErrorInfo(
                source=source,
                error_type="connection_error",
                error_message=f"Connection failed: {error_message}",
                is_temporary=True,
                suggested_action="Check network connectivity. Retry after brief delay.",
                timestamp=datetime.now()
            )
        
        # Not found errors
        if any(pattern in error_lower for pattern in ['404', 'not found', 'no data']):
            return ErrorInfo(
                source=source,
                error_type="not_found",
                error_message=f"Resource not found: {error_message}",
                is_temporary=False,
                suggested_action="Verify ticker symbol or parameters. Check if data exists for this ticker.",
                timestamp=datetime.now()
            )
        
        # Authentication errors
        if any(pattern in error_lower for pattern in ['401', 'unauthorized', 'authentication', 'api key']):
            return ErrorInfo(
                source=source,
                error_type="unauthorized",
                error_message=f"Authentication failed: {error_message}",
                is_temporary=False,
                suggested_action="Check API key configuration in environment variables.",
                timestamp=datetime.now()
            )
        
        # Service unavailable
        if any(pattern in error_lower for pattern in ['503', 'unavailable', 'service down']):
            return ErrorInfo(
                source=source,
                error_type="service_unavailable",
                error_message=f"Service unavailable: {error_message}",
                is_temporary=True,
                suggested_action="Service is temporarily down. Retry after 60 seconds or use alternative source.",
                timestamp=datetime.now()
            )
        
        # Bad request
        if any(pattern in error_lower for pattern in ['400', 'bad request', 'invalid']):
            return ErrorInfo(
                source=source,
                error_type="bad_request",
                error_message=f"Invalid request: {error_message}",
                is_temporary=False,
                suggested_action="Check request parameters. Verify ticker format and date ranges.",
                timestamp=datetime.now()
            )
        
        # Parsing errors
        if any(pattern in error_lower for pattern in ['parse', 'json', 'xml', 'decode']):
            return ErrorInfo(
                source=source,
                error_type="parse_error",
                error_message=f"Failed to parse response: {error_message}",
                is_temporary=True,
                suggested_action="API response format may have changed. Try alternative source.",
                timestamp=datetime.now()
            )
        
        # Generic API error
        return ErrorInfo(
            source=source,
            error_type="api_error",
            error_message=f"API error ({error_class}): {error_message}",
            is_temporary=True,
            suggested_action="Check error details and retry. If persists, try alternative source.",
            timestamp=datetime.now()
        )
    
    def _classify_http_error(
        self,
        source: str,
        status_code: int,
        error_message: str,
        context: Optional[str] = None
    ) -> ErrorInfo:
        """
        Classify HTTP status code errors.
        
        Args:
            source: Source name
            status_code: HTTP status code
            error_message: Error message
            context: Optional context
            
        Returns:
            ErrorInfo object
        """
        context_msg = f" ({context})" if context else ""
        
        # 4xx Client Errors
        if status_code == 400:
            return ErrorInfo(
                source=source,
                error_type="bad_request",
                error_message=f"Bad request{context_msg}: {error_message}",
                is_temporary=False,
                suggested_action="Check request parameters. Verify ticker format and date ranges.",
                timestamp=datetime.now()
            )
        
        elif status_code == 401:
            return ErrorInfo(
                source=source,
                error_type="unauthorized",
                error_message=f"Unauthorized{context_msg}: {error_message}",
                is_temporary=False,
                suggested_action="Check API key configuration in environment variables.",
                timestamp=datetime.now()
            )
        
        elif status_code == 403:
            return ErrorInfo(
                source=source,
                error_type="forbidden",
                error_message=f"Access forbidden{context_msg}: {error_message}",
                is_temporary=False,
                suggested_action="API access denied. Check permissions or subscription status.",
                timestamp=datetime.now()
            )
        
        elif status_code == 404:
            return ErrorInfo(
                source=source,
                error_type="not_found",
                error_message=f"Resource not found{context_msg}: {error_message}",
                is_temporary=False,
                suggested_action="Verify ticker symbol or parameters. Check if data exists for this ticker.",
                timestamp=datetime.now()
            )
        
        elif status_code == 429:
            return ErrorInfo(
                source=source,
                error_type="rate_limit",
                error_message=f"Rate limit exceeded{context_msg}: {error_message}",
                is_temporary=True,
                suggested_action="Retry with exponential backoff (10s, 20s, 40s). Consider using alternative source.",
                timestamp=datetime.now()
            )
        
        # 5xx Server Errors
        elif status_code == 500:
            return ErrorInfo(
                source=source,
                error_type="server_error",
                error_message=f"Internal server error{context_msg}: {error_message}",
                is_temporary=True,
                suggested_action="Server error. Retry after brief delay or use alternative source.",
                timestamp=datetime.now()
            )
        
        elif status_code == 502:
            return ErrorInfo(
                source=source,
                error_type="bad_gateway",
                error_message=f"Bad gateway{context_msg}: {error_message}",
                is_temporary=True,
                suggested_action="Gateway error. Retry after brief delay or use alternative source.",
                timestamp=datetime.now()
            )
        
        elif status_code == 503:
            return ErrorInfo(
                source=source,
                error_type="service_unavailable",
                error_message=f"Service unavailable{context_msg}: {error_message}",
                is_temporary=True,
                suggested_action="Service is temporarily down. Retry after 60 seconds or use alternative source.",
                timestamp=datetime.now()
            )
        
        elif status_code == 504:
            return ErrorInfo(
                source=source,
                error_type="gateway_timeout",
                error_message=f"Gateway timeout{context_msg}: {error_message}",
                is_temporary=True,
                suggested_action="Request timeout at gateway. Retry with increased timeout.",
                timestamp=datetime.now()
            )
        
        # Other status codes
        else:
            is_temporary = status_code >= 500  # 5xx are temporary, 4xx are permanent
            action = (
                "Server error - retry after delay or use alternative source."
                if is_temporary
                else "Client error - check request parameters."
            )
            
            return ErrorInfo(
                source=source,
                error_type=f"http_{status_code}",
                error_message=f"HTTP {status_code}{context_msg}: {error_message}",
                is_temporary=is_temporary,
                suggested_action=action,
                timestamp=datetime.now()
            )
    
    def is_retryable(self, error_info: ErrorInfo) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error_info: ErrorInfo object
            
        Returns:
            True if error is temporary and should be retried
        """
        return error_info.is_temporary
    
    def get_retry_delay(self, error_info: ErrorInfo, attempt: int) -> float:
        """
        Get recommended retry delay based on error type.
        
        Args:
            error_info: ErrorInfo object
            attempt: Retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Rate limit errors need longer delays
        if error_info.error_type == "rate_limit":
            return min(10.0 * (2 ** attempt), 60.0)  # 10s, 20s, 40s, 60s max
        
        # Service unavailable needs moderate delays
        elif error_info.error_type in ["service_unavailable", "server_error"]:
            return min(5.0 * (2 ** attempt), 30.0)  # 5s, 10s, 20s, 30s max
        
        # Timeout and connection errors need shorter delays
        elif error_info.error_type in ["timeout", "connection_error"]:
            return min(2.0 * (2 ** attempt), 10.0)  # 2s, 4s, 8s, 10s max
        
        # Default exponential backoff
        else:
            return min(1.0 * (2 ** attempt), 10.0)  # 1s, 2s, 4s, 8s, 10s max
