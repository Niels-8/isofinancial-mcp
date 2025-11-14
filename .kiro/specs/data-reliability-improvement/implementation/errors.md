# Error Handling and Reporting Implementation

## Overview

This document describes the implementation of comprehensive error handling and reporting improvements for the IsoFinancial-MCP reliability infrastructure.

## Components Implemented

### 1. ErrorHandler Class (`error_handler.py`)

A dedicated class for classifying and managing errors with actionable suggestions.

**Key Features:**
- Comprehensive error classification based on exception types and HTTP status codes
- Distinguishes between temporary (retryable) and permanent errors
- Generates actionable error messages with specific suggested actions
- Supports context-aware error classification

**Error Types Classified:**
- `rate_limit` (429) - Temporary, retry with exponential backoff
- `timeout` - Temporary, retry with increased timeout
- `connection_error` - Temporary, check network connectivity
- `not_found` (404) - Permanent, verify ticker/parameters
- `unauthorized` (401) - Permanent, check API key configuration
- `forbidden` (403) - Permanent, check permissions
- `service_unavailable` (503) - Temporary, retry after delay
- `bad_request` (400) - Permanent, check request parameters
- `server_error` (500) - Temporary, retry after delay
- `bad_gateway` (502) - Temporary, retry after delay
- `gateway_timeout` (504) - Temporary, retry with increased timeout
- `parse_error` - Temporary, API response format may have changed
- `api_error` - Generic temporary error

**Methods:**
```python
classify_error(source: str, error: Exception, context: Optional[str] = None) -> ErrorInfo
is_retryable(error_info: ErrorInfo) -> bool
get_retry_delay(error_info: ErrorInfo, attempt: int) -> float
```

### 2. Enhanced DataResult Model

Extended the `DataResult` model to include comprehensive partial data tracking.

**New Fields:**
- `successful_sources: List[str]` - List of sources that succeeded
- `failed_sources: List[str]` - List of sources that failed
- `last_successful_update: Optional[datetime]` - Timestamp of last successful data fetch

**Existing Fields Enhanced:**
- `partial_data: bool` - Now properly tracked based on success/failure mix
- `errors: List[ErrorInfo]` - Contains detailed error information with suggested actions

### 3. DataManager Integration

Updated `DataManager` to use the `ErrorHandler` class for consistent error classification.

**Changes:**
- Added `error_handler` parameter to constructor
- Replaced internal `_classify_error` method with `ErrorHandler.classify_error`
- Enhanced all `DataResult` returns to include `successful_sources`, `failed_sources`, and `last_successful_update`
- Properly tracks partial data scenarios (some sources succeed, some fail)

### 4. Source Manager Updates

Updated all three source managers to use `ErrorHandler` and track partial data:

#### SECSourceManager
- Added `error_handler` parameter to constructor
- Uses `ErrorHandler` for consistent error classification
- Tracks attempted, successful, and failed sources

#### TrendsSourceManager
- Added `error_handler` parameter to constructor
- Uses `ErrorHandler.classify_error` for error classification
- Enhanced `DataResult` returns with partial data tracking
- Properly handles stale cache scenarios with partial data flag

#### EarningsSourceManager
- Added `error_handler` parameter to constructor
- Uses `ErrorHandler.classify_error` for parallel fetch error handling
- Tracks which sources succeeded and which failed during data fusion
- Sets `partial_data=True` when some sources succeed and others fail

## Error Classification Examples

### Rate Limit Error (429)
```python
ErrorInfo(
    source="pytrends_direct",
    error_type="rate_limit",
    error_message="Rate limit exceeded: 429 Too Many Requests",
    is_temporary=True,
    suggested_action="Retry with exponential backoff (10s, 20s, 40s). Consider using alternative source."
)
```

### Not Found Error (404)
```python
ErrorInfo(
    source="sec_edgar_api",
    error_type="not_found",
    error_message="Resource not found: 404 Not Found",
    is_temporary=False,
    suggested_action="Verify ticker symbol or parameters. Check if data exists for this ticker."
)
```

### Timeout Error
```python
ErrorInfo(
    source="nasdaq",
    error_type="timeout",
    error_message="Request timeout: Connection timed out",
    is_temporary=True,
    suggested_action="Retry with increased timeout. Check network connectivity."
)
```

## Partial Data Handling

### Scenario 1: Some Sources Succeed
When fetching from multiple sources in parallel (e.g., earnings data):
```python
DataResult(
    data=[...],  # Merged data from successful sources
    source_used="nasdaq+alpha_vantage",
    successful_sources=["nasdaq", "alpha_vantage"],
    failed_sources=["yahoo_finance"],
    partial_data=True,  # Some sources failed
    errors=[ErrorInfo(...)]  # Details about yahoo_finance failure
)
```

### Scenario 2: All Sources Fail, Stale Cache Available
```python
DataResult(
    data=[...],  # Stale cached data
    source_used="nasdaq",
    is_cached=True,
    is_stale=True,
    cache_age_seconds=7200,
    successful_sources=[],
    failed_sources=["nasdaq", "alpha_vantage", "yahoo_finance"],
    partial_data=True,  # Using stale data is partial data
    last_successful_update=datetime(2025, 11, 13, 10, 0, 0),
    errors=[ErrorInfo(...), ErrorInfo(...), ErrorInfo(...)]
)
```

### Scenario 3: All Sources Fail, No Cache
```python
DataResult(
    data=None,
    source_used="none",
    successful_sources=[],
    failed_sources=["source1", "source2", "source3"],
    partial_data=False,  # No data at all
    errors=[ErrorInfo(...), ErrorInfo(...), ErrorInfo(...)]
)
```

## Retry Delay Recommendations

The `ErrorHandler.get_retry_delay()` method provides intelligent retry delays based on error type:

- **Rate Limit Errors**: 10s, 20s, 40s, 60s (max)
- **Service Unavailable**: 5s, 10s, 20s, 30s (max)
- **Timeout/Connection**: 2s, 4s, 8s, 10s (max)
- **Other Temporary**: 1s, 2s, 4s, 8s, 10s (max)

## Usage Examples

### Using ErrorHandler Directly
```python
from iso_financial_mcp.reliability import ErrorHandler

handler = ErrorHandler()

try:
    # Some API call
    response = await api_call()
except Exception as e:
    error_info = handler.classify_error(
        source="my_api",
        error=e,
        context="fetching ticker data"
    )
    
    if handler.is_retryable(error_info):
        delay = handler.get_retry_delay(error_info, attempt=0)
        await asyncio.sleep(delay)
        # Retry logic
```

### Using DataManager with ErrorHandler
```python
from iso_financial_mcp.reliability import DataManager, ErrorHandler

data_manager = DataManager(error_handler=ErrorHandler())

result = await data_manager.fetch_with_fallback(
    cache_key="my_data",
    sources=[
        ("source1", fetch_func1),
        ("source2", fetch_func2)
    ],
    ticker="AAPL"
)

if result.partial_data:
    print(f"Warning: Partial data from {result.successful_sources}")
    print(f"Failed sources: {result.failed_sources}")
    for error in result.errors:
        print(f"  - {error.source}: {error.suggested_action}")
```

## Testing

The implementation has been validated with:

1. **ErrorHandler Classification Tests**
   - Rate limit errors correctly classified as temporary
   - Not found errors correctly classified as permanent
   - Timeout errors correctly classified as temporary
   - Suggested actions are actionable and specific

2. **DataResult Partial Data Tests**
   - Successful sources tracked correctly
   - Failed sources tracked correctly
   - Partial data flag set appropriately
   - Last successful update timestamp recorded

3. **Integration Tests**
   - DataManager uses ErrorHandler for classification
   - Source managers properly track partial data
   - Error information flows through the entire stack

## Requirements Satisfied

This implementation satisfies the following requirements:

- **Requirement 6.1**: Structured error responses with error_type, error_message, attempted_sources, fallback_used
- **Requirement 6.2**: Distinction between temporary and permanent errors
- **Requirement 6.3**: Partial data handling with source tracking
- **Requirement 6.4**: Last successful update timestamp included
- **Requirement 6.5**: Actionable error messages with suggested corrective actions

## Future Enhancements

Potential improvements for future iterations:

1. **Error Aggregation**: Aggregate similar errors across multiple requests
2. **Error Metrics**: Track error rates and patterns over time
3. **Smart Retry**: Use error history to optimize retry strategies
4. **Error Notifications**: Alert on persistent error patterns
5. **Error Recovery**: Automatic recovery strategies for common error scenarios
