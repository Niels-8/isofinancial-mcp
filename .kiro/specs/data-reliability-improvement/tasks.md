# Implementation Plan

- [x] 1. Set up core infrastructure components
  - Create base classes and interfaces for Data Manager, Cache Layer, and Health Monitor
  - Define data models (DataResult, HealthStatus, ErrorInfo, CachedData)
  - Set up configuration loading from YAML file
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 1.1 Implement Cache Layer with two-level caching
  - Create CacheLayer class with memory cache (TTLCache) and disk cache
  - Implement get() method with allow_stale parameter for expired data fallback
  - Implement set() method to store in both memory and disk
  - Add cache key generation utilities
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 1.2 Implement Health Monitor for source tracking
  - Create HealthMonitor class with metrics storage
  - Implement record_request() to track success/failure/latency
  - Implement get_health_status() to calculate success rate and status
  - Add JSONL logging for metrics persistence
  - Implement unhealthy source detection (>30% failure rate)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 1.3 Implement Data Manager orchestration layer
  - Create DataManager class with fetch_with_fallback() method
  - Implement source iteration with error handling
  - Add cache integration (check before fetch, store after)
  - Implement stale data fallback when all sources fail
  - _Requirements: 1.5, 5.2, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 1.4 Implement Source Router for intelligent source selection
  - Create SourceRouter class with get_ordered_sources() method
  - Implement source prioritization based on health metrics
  - Add logic to skip unhealthy sources (success_rate < 30%)
  - _Requirements: 4.5_

- [x] 2. Implement SEC Source improvements with fallback
  - Add alternative SEC data sources (RSS feeds, XBRL API)
  - Implement automatic lookback extension (30 days → 90 days)
  - Add source fallback logic in SECSourceManager
  - Integrate with Data Manager and Cache Layer
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2.1 Create SEC RSS Feed source implementation
  - Implement SECRSSFeed class to parse SEC RSS feeds
  - Add parsing logic for form types and dates
  - Handle RSS feed errors gracefully
  - _Requirements: 1.1, 1.2_

- [x] 2.2 Create SEC XBRL API source implementation
  - Implement SECXBRLApi class as third fallback source
  - Add XBRL data parsing and normalization
  - _Requirements: 1.1, 1.2_

- [x] 2.3 Implement SECSourceManager with multi-source fallback
  - Create SECSourceManager class with ordered source list
  - Implement fetch_filings() with automatic fallback
  - Add automatic lookback extension when no results found
  - Integrate stale cache fallback as last resort
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3. Implement Google Trends improvements with rate limit handling
  - Add exponential backoff retry strategy for 429 errors
  - Implement adaptive rate limiter with slow mode
  - Add alternative sources (proxy, SerpAPI)
  - Integrate with Data Manager
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3.1 Implement adaptive rate limiter for Trends
  - Create AdaptiveRateLimiter class with configurable delays
  - Implement error rate tracking (last 10 requests)
  - Add automatic slow mode activation (>50% errors → 10s delay)
  - Reduce default rate from 1/3s to 1/5s
  - _Requirements: 2.2, 2.5_

- [x] 3.2 Implement retry strategy with exponential backoff
  - Create RetryStrategy class with configurable parameters
  - Implement get_next_delay() with exponential backoff (10s, 20s, 40s)
  - Add random jitter (1-3 seconds) to avoid detection patterns
  - _Requirements: 2.1, 2.4_

- [x] 3.3 Add PyTrends with proxy as fallback source
  - Implement PyTrendsWithProxy class
  - Add proxy configuration support
  - Integrate as second priority source
  - _Requirements: 2.3_

- [x] 3.4 Add SerpAPI as final Trends fallback
  - Implement SerpAPIFallback class
  - Add API key configuration from environment
  - Integrate as third priority source
  - _Requirements: 2.3_

- [x] 3.5 Integrate Trends improvements into TrendsSourceManager
  - Create TrendsSourceManager with ordered sources
  - Implement fetch_trends() with retry and fallback logic
  - Add 429 error detection and backoff handling
  - Integrate with adaptive rate limiter
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 4. Implement Earnings Calendar improvements with multi-source fusion
  - Add alternative earnings sources (Nasdaq, Alpha Vantage)
  - Implement data fusion and deduplication
  - Add earnings date estimation fallback
  - Validate that at least one future date exists
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4.1 Add Nasdaq API as earnings source
  - Refactor existing Nasdaq implementation into NasdaqEarnings class
  - Improve error handling for None/non-iterable responses
  - _Requirements: 3.1, 3.2_

- [x] 4.2 Add Alpha Vantage as earnings source
  - Implement AlphaVantageEarnings class
  - Add API key configuration from environment
  - Parse Alpha Vantage earnings response format
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 4.3 Implement earnings data fusion logic
  - Create data merging function with deduplication by date
  - Handle different date formats from various sources
  - Prioritize data quality (prefer sources with EPS estimates)
  - _Requirements: 3.3_

- [x] 4.4 Implement earnings date estimation
  - Create estimate_next_earnings() method
  - Calculate next earnings based on quarter end dates + 45 days
  - Use historical patterns if available
  - _Requirements: 3.4_

- [x] 4.5 Implement EarningsSourceManager with fusion
  - Create EarningsSourceManager with ordered sources
  - Implement fetch_earnings() with parallel source fetching
  - Add data fusion and deduplication
  - Implement estimation fallback when no data available
  - Add validation for at least one future date
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. Implement error handling and reporting improvements
  - Create ErrorHandler class with error classification
  - Implement structured error responses with ErrorInfo
  - Add actionable error messages with suggested actions
  - Distinguish temporary vs permanent errors
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5.1 Implement error classification logic
  - Create classify_error() method for exception types
  - Map HTTP status codes to error types (429→rate_limit, 404→not_found)
  - Determine if error is temporary or permanent
  - Generate suggested actions for each error type
  - _Requirements: 6.1, 6.2, 6.5_

- [x] 5.2 Update all source managers to use ErrorInfo
  - Modify SEC, Trends, and Earnings managers to return ErrorInfo
  - Include attempted_sources list in responses
  - Add fallback_used flag to indicate which source succeeded
  - _Requirements: 6.1, 6.3_

- [x] 5.3 Add partial data handling
  - Implement partial_data flag in DataResult
  - Track which sources succeeded and which failed
  - Include last successful update timestamp
  - _Requirements: 6.3, 6.4_

- [x] 6. Integration with existing meta_tools
  - Update get_financial_snapshot() to use new Data Manager
  - Maintain backward compatibility with existing API
  - Add error information to snapshot responses
  - Update format_snapshot_for_llm() to display new error details
  - _Requirements: All requirements_

- [x] 6.1 Refactor meta_tools to use Data Manager
  - Replace direct datasource calls with DataManager.fetch_with_fallback()
  - Update error handling to use new ErrorInfo structure
  - Maintain existing response format for compatibility
  - _Requirements: All requirements_

- [x] 6.2 Update snapshot formatting for new error details
  - Modify format_snapshot_for_llm() to show source used
  - Display cache status (fresh, stale, age)
  - Show attempted sources and fallback information
  - Format actionable error messages
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7. Configuration and deployment
  - Create datasources.yaml configuration file
  - Add environment variable support for API keys
  - Create migration guide for existing users
  - Update documentation with new features
  - _Requirements: All requirements_

- [x] 7.1 Create configuration file structure
  - Create config/datasources.yaml with all source configurations
  - Add rate limiting, retry, and cache settings
  - Document all configuration options
  - _Requirements: All requirements_

- [x] 7.2 Implement configuration loader
  - Create ConfigLoader class to parse YAML
  - Add validation for required fields
  - Support environment variable substitution
  - Provide sensible defaults
  - _Requirements: All requirements_

- [ ] 8. Testing and validation
  - Write unit tests for all new components
  - Create integration tests for end-to-end flows
  - Add performance tests for cache and parallel requests
  - Test rate limiting and retry logic
  - _Requirements: All requirements_

- [x] 8.1 Write unit tests for Cache Layer
  - Test memory cache with TTL expiration
  - Test disk cache persistence
  - Test stale data fallback
  - Test cache key generation
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8.2 Write unit tests for Health Monitor
  - Test success rate calculation
  - Test unhealthy source detection
  - Test metrics logging
  - Test health status reporting
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 8.3 Write unit tests for Source Managers
  - Test SEC fallback logic
  - Test Trends retry with backoff
  - Test Earnings data fusion
  - Test error classification
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

- [ ] 8.4 Write integration tests for end-to-end flows
  - Test complete flow with all sources failing
  - Test flow with stale cache fallback
  - Test flow with partial data
  - Test parallel multi-ticker requests
  - _Requirements: All requirements_

- [ ] 8.5 Write performance tests
  - Test cache hit rate with 1000+ tickers
  - Test parallel request throughput
  - Test rate limiter effectiveness
  - Measure latency improvements
  - _Requirements: 5.4, 5.5_
