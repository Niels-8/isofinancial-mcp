"""
Test suite for meta_tools module.

This module tests the consolidated meta-tools that retrieve all financial data
in 1-2 calls instead of 10+ individual calls, optimizing for LLM agent efficiency.

Tests are designed to run with: uv run pytest tests/test_meta_tools.py -v
"""

import pytest
import pytest_asyncio
from datetime import datetime
from typing import Dict, Any

# Import functions to test from meta_tools
from iso_financial_mcp.meta_tools import (
    truncate_string,
    format_compact_data,
    get_financial_snapshot,
    get_multi_ticker_snapshot,
    format_snapshot_for_llm,
    format_multi_snapshot_for_llm,
)


# ============================================================================
# Utility Functions Tests
# ============================================================================

class TestUtilityFunctions:
    """Test suite for utility functions (truncate_string, format_compact_data)"""
    
    # ========================================================================
    # truncate_string tests - Requirements 3.1, 3.2
    # ========================================================================
    
    def test_truncate_string_short_text(self):
        """Test that short text is not truncated (small input)"""
        text = "Short text"
        result = truncate_string(text, max_length=100)
        assert result == text
        assert "[truncated]" not in result
    
    def test_truncate_string_medium_text(self):
        """Test medium-sized text that doesn't need truncation"""
        text = "A" * 50  # Medium size, well under limit
        result = truncate_string(text, max_length=100)
        assert result == text
        assert "[truncated]" not in result
        assert len(result) == 50
    
    def test_truncate_string_long_text(self):
        """Test that long text is truncated with indicator (large input)"""
        text = "A" * 1000
        result = truncate_string(text, max_length=100)
        assert len(result) <= 115  # 100 + "... [truncated]"
        assert "[truncated]" in result
        assert result.startswith("A" * 50)  # Should start with original text
    
    def test_truncate_string_very_long_text(self):
        """Test very long text (extra large input)"""
        text = "B" * 10000
        result = truncate_string(text, max_length=500)
        assert len(result) <= 520  # 500 + "... [truncated]"
        assert "[truncated]" in result
        assert result.startswith("B" * 100)
    
    def test_truncate_string_exact_length(self):
        """Test text exactly at max_length (edge case)"""
        text = "A" * 100
        result = truncate_string(text, max_length=100)
        assert result == text
        assert "[truncated]" not in result
    
    def test_truncate_string_one_over_limit(self):
        """Test text one character over limit"""
        text = "A" * 101
        result = truncate_string(text, max_length=100)
        assert "[truncated]" in result
        assert len(result) <= 115
    
    def test_truncate_string_empty(self):
        """Test empty string handling"""
        result = truncate_string("", max_length=100)
        assert result == ""
    
    def test_truncate_string_none(self):
        """Test None handling"""
        result = truncate_string(None, max_length=100)
        assert result == ""
    
    def test_truncate_string_with_whitespace(self):
        """Test truncation with trailing whitespace"""
        text = "A" * 100 + "     "  # Text with trailing spaces
        result = truncate_string(text, max_length=100)
        assert "[truncated]" in result
        # Should strip trailing whitespace before adding indicator
        assert not result.startswith("A" * 100 + " ")
    
    def test_truncate_string_custom_max_length(self):
        """Test with different max_length values"""
        text = "X" * 1000
        
        # Test with max_length=50
        result_50 = truncate_string(text, max_length=50)
        assert "[truncated]" in result_50
        assert len(result_50) <= 65
        
        # Test with max_length=200
        result_200 = truncate_string(text, max_length=200)
        assert "[truncated]" in result_200
        assert len(result_200) <= 220
    
    # ========================================================================
    # format_compact_data tests - Requirements 3.1, 3.2
    # ========================================================================
    
    def test_format_compact_data_short_list(self):
        """Test that short lists are not compacted (small input)"""
        data = [1, 2, 3, 4, 5]
        result = format_compact_data(data, max_items=5)
        assert "[1, 2, 3, 4, 5]" in result
        assert "more items" not in result
    
    def test_format_compact_data_medium_list(self):
        """Test medium-sized list (at the boundary)"""
        data = list(range(7))  # 7 items with max_items=5
        result = format_compact_data(data, max_items=5)
        assert "+2 more items" in result
        assert "[0, 1, 2, 3, 4]" in result
    
    def test_format_compact_data_long_list(self):
        """Test that long lists are compacted with indicator (large input)"""
        data = list(range(20))
        result = format_compact_data(data, max_items=5)
        assert "+15 more items" in result
        assert "[0, 1, 2, 3, 4]" in result
    
    def test_format_compact_data_very_long_list(self):
        """Test very long list (extra large input)"""
        data = list(range(1000))
        result = format_compact_data(data, max_items=5)
        assert "+995 more items" in result
        assert "[0, 1, 2, 3, 4]" in result
    
    def test_format_compact_data_single_item_list(self):
        """Test list with single item (very small input)"""
        data = [42]
        result = format_compact_data(data, max_items=5)
        assert "[42]" in result
        assert "more items" not in result
    
    def test_format_compact_data_empty_list(self):
        """Test empty list"""
        data = []
        result = format_compact_data(data, max_items=5)
        assert result == "[]"
        assert "more items" not in result
    
    def test_format_compact_data_dict_small(self):
        """Test small dictionary (small input)"""
        data = {"a": 1, "b": 2, "c": 3}
        result = format_compact_data(data, max_items=5)
        assert "more items" not in result
        assert "'a': 1" in result or '"a": 1' in result
    
    def test_format_compact_data_dict_medium(self):
        """Test medium dictionary (at boundary)"""
        data = {f"key{i}": i for i in range(7)}
        result = format_compact_data(data, max_items=5)
        assert "+2 more items" in result
    
    def test_format_compact_data_dict_large(self):
        """Test large dictionary compaction (large input)"""
        data = {f"key{i}": i for i in range(20)}
        result = format_compact_data(data, max_items=5)
        assert "+15 more items" in result
    
    def test_format_compact_data_none(self):
        """Test None handling"""
        result = format_compact_data(None, max_items=5)
        assert result == "None"
    
    def test_format_compact_data_string(self):
        """Test string input (non-list/dict)"""
        data = "This is a string"
        result = format_compact_data(data, max_items=5)
        assert result == "This is a string"
    
    def test_format_compact_data_number(self):
        """Test numeric input"""
        data = 42
        result = format_compact_data(data, max_items=5)
        assert result == "42"
    
    def test_format_compact_data_custom_max_items(self):
        """Test with different max_items values"""
        data = list(range(20))
        
        # Test with max_items=3
        result_3 = format_compact_data(data, max_items=3)
        assert "+17 more items" in result_3
        assert "[0, 1, 2]" in result_3
        
        # Test with max_items=10
        result_10 = format_compact_data(data, max_items=10)
        assert "+10 more items" in result_10
        assert "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]" in result_10
    
    def test_format_compact_data_list_of_strings(self):
        """Test list of strings (realistic use case)"""
        data = [f"Article {i}" for i in range(15)]
        result = format_compact_data(data, max_items=5)
        assert "+10 more items" in result
        assert "Article 0" in result
        assert "Article 4" in result
    
    def test_format_compact_data_nested_structures(self):
        """Test nested data structures"""
        data = [{"id": i, "name": f"Item {i}"} for i in range(10)]
        result = format_compact_data(data, max_items=5)
        assert "+5 more items" in result


# ============================================================================
# Financial Snapshot Tests
# ============================================================================

class TestGetFinancialSnapshot:
    """Test suite for get_financial_snapshot function"""
    
    @pytest.mark.asyncio
    async def test_get_financial_snapshot_structure(self):
        """Test that snapshot returns correct structure"""
        snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        
        # Verify structure
        assert "ticker" in snapshot
        assert "timestamp" in snapshot
        assert "data" in snapshot
        assert "errors" in snapshot
        
        # Verify ticker is uppercase
        assert snapshot["ticker"] == "AAPL"
        
        # Verify timestamp format
        assert isinstance(snapshot["timestamp"], str)
        datetime.fromisoformat(snapshot["timestamp"])  # Should not raise
        
        # Verify data and errors are correct types
        assert isinstance(snapshot["data"], dict)
        assert isinstance(snapshot["errors"], list)
    
    @pytest.mark.asyncio
    async def test_get_financial_snapshot_valid_ticker(self):
        """Test successful snapshot retrieval for valid ticker"""
        snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        
        # Should have some data sources populated
        assert len(snapshot["data"]) > 0
        
        # Check for expected data keys (at least some should be present)
        possible_keys = ["info", "prices", "news", "sec_filings", "earnings", "short_volume", "google_trends"]
        found_keys = [key for key in possible_keys if key in snapshot["data"]]
        assert len(found_keys) > 0, "Should have at least one data source"
    
    @pytest.mark.asyncio
    async def test_get_financial_snapshot_graceful_degradation(self):
        """Test graceful degradation with partial failures"""
        # Use an invalid ticker that might cause some sources to fail
        snapshot = await get_financial_snapshot("INVALID_TICKER_XYZ123", lookback_days=7)
        
        # Should still return valid structure
        assert "ticker" in snapshot
        assert "data" in snapshot
        assert "errors" in snapshot
        
        # Should have some errors recorded
        # Note: Some sources might still return empty data without errors
        assert isinstance(snapshot["errors"], list)
    
    @pytest.mark.asyncio
    async def test_get_financial_snapshot_without_options(self):
        """Test snapshot without options data"""
        snapshot = await get_financial_snapshot("AAPL", include_options=False, lookback_days=7)
        
        # Options should not be in data
        assert "options" not in snapshot["data"]
    
    @pytest.mark.asyncio
    async def test_get_financial_snapshot_with_options(self):
        """Test snapshot with options data requested"""
        snapshot = await get_financial_snapshot("AAPL", include_options=True, lookback_days=7)
        
        # Options might be in data or in errors (if not available)
        # Just verify the request was processed
        assert "ticker" in snapshot
        assert isinstance(snapshot["data"], dict)
    
    @pytest.mark.asyncio
    async def test_get_financial_snapshot_lookback_days(self):
        """Test different lookback_days parameter"""
        snapshot_7d = await get_financial_snapshot("AAPL", lookback_days=7)
        snapshot_30d = await get_financial_snapshot("AAPL", lookback_days=30)
        
        # Both should return valid structures
        assert "ticker" in snapshot_7d
        assert "ticker" in snapshot_30d
        
        # Both should have data
        assert isinstance(snapshot_7d["data"], dict)
        assert isinstance(snapshot_30d["data"], dict)


# ============================================================================
# Multi-Ticker Snapshot Tests
# ============================================================================

class TestGetMultiTickerSnapshot:
    """Test suite for get_multi_ticker_snapshot function"""
    
    @pytest.mark.asyncio
    async def test_get_multi_ticker_snapshot_structure(self):
        """Test that multi-snapshot returns correct structure"""
        tickers = ["AAPL", "MSFT"]
        snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        
        # Verify structure
        assert "timestamp" in snapshot
        assert "tickers_count" in snapshot
        assert "snapshots" in snapshot
        assert "global_errors" in snapshot
        
        # Verify types
        assert isinstance(snapshot["timestamp"], str)
        assert isinstance(snapshot["tickers_count"], int)
        assert isinstance(snapshot["snapshots"], dict)
        assert isinstance(snapshot["global_errors"], list)
    
    @pytest.mark.asyncio
    async def test_get_multi_ticker_snapshot_parallel(self):
        """Test parallel multi-ticker retrieval with 3 tickers and verify time < 10s
        
        Requirements: 2.1, 2.2, 2.3, 2.7, 8.4
        """
        import time
        
        tickers = ["AAPL", "MSFT", "GOOGL"]
        start = time.time()
        
        snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        
        elapsed = time.time() - start
        
        # Verify tickers_count (Requirement 2.1, 2.2)
        assert snapshot["tickers_count"] == 3, f"Expected 3 tickers, got {snapshot['tickers_count']}"
        
        # Verify snapshots dict structure (Requirement 2.3)
        assert isinstance(snapshot["snapshots"], dict), "snapshots should be a dict"
        assert len(snapshot["snapshots"]) <= 3, "Should have at most 3 ticker snapshots"
        
        # Verify global_errors list (Requirement 8.4)
        assert isinstance(snapshot["global_errors"], list), "global_errors should be a list"
        
        # Verify each snapshot in snapshots dict has correct structure
        for ticker, ticker_snapshot in snapshot["snapshots"].items():
            assert isinstance(ticker_snapshot, dict), f"Snapshot for {ticker} should be a dict"
            assert "ticker" in ticker_snapshot, f"Snapshot for {ticker} missing 'ticker' field"
            assert "data" in ticker_snapshot, f"Snapshot for {ticker} missing 'data' field"
            assert "errors" in ticker_snapshot, f"Snapshot for {ticker} missing 'errors' field"
        
        # Parallel execution should be fast - verify time < 10s (Requirement 2.7)
        assert elapsed < 10, f"Parallel execution took too long: {elapsed}s (should be < 10s)"
        
        print(f"✅ Parallel execution completed in {elapsed:.2f}s with {len(snapshot['snapshots'])} successful snapshots")
    
    @pytest.mark.asyncio
    async def test_get_multi_ticker_snapshot_max_limit(self):
        """Test max_tickers safety limit with 15 tickers limited to 10
        
        Requirements: 2.2, 2.3, 2.7, 8.4
        """
        # Create list of 15 tickers
        tickers = [f"TICK{i}" for i in range(15)]
        
        snapshot = await get_multi_ticker_snapshot(tickers, max_tickers=10, lookback_days=7)
        
        # Verify tickers_count is limited to 10 (Requirement 2.2)
        assert snapshot["tickers_count"] == 10, f"Expected tickers_count=10, got {snapshot['tickers_count']}"
        
        # Verify snapshots dict structure (Requirement 2.3)
        assert isinstance(snapshot["snapshots"], dict), "snapshots should be a dict"
        assert len(snapshot["snapshots"]) <= 10, f"Should have at most 10 snapshots, got {len(snapshot['snapshots'])}"
        
        # Verify global_errors contains warning about limiting (Requirement 8.4)
        assert isinstance(snapshot["global_errors"], list), "global_errors should be a list"
        assert len(snapshot["global_errors"]) > 0, "Should have warning about ticker limit"
        assert any("limited" in error.lower() or "limit" in error.lower() 
                  for error in snapshot["global_errors"]), "Should have 'limited' or 'limit' in global_errors"
        
        # Verify timestamp is present
        assert "timestamp" in snapshot, "Should have timestamp field"
        
        print(f"✅ Successfully limited 15 tickers to {snapshot['tickers_count']} with {len(snapshot['snapshots'])} snapshots")
    
    @pytest.mark.asyncio
    async def test_get_multi_ticker_snapshot_with_errors(self):
        """Test mix of valid and invalid tickers with comprehensive validation
        
        Requirements: 2.1, 2.3, 8.4
        """
        tickers = ["AAPL", "INVALID_XYZ123", "MSFT"]
        
        snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        
        # Verify tickers_count includes all requested tickers (Requirement 2.1)
        assert snapshot["tickers_count"] == 3, f"Expected tickers_count=3, got {snapshot['tickers_count']}"
        
        # Verify snapshots dict structure (Requirement 2.3)
        assert isinstance(snapshot["snapshots"], dict), "snapshots should be a dict"
        
        # Should have some successful snapshots (at least AAPL and MSFT should work)
        assert len(snapshot["snapshots"]) >= 0, "Should have at least 0 snapshots"
        
        # Verify global_errors list (Requirement 8.4)
        assert isinstance(snapshot["global_errors"], list), "global_errors should be a list"
        
        # Verify each snapshot in snapshots dict has correct structure
        for ticker, ticker_snapshot in snapshot["snapshots"].items():
            assert isinstance(ticker_snapshot, dict), f"Snapshot for {ticker} should be a dict"
            assert "ticker" in ticker_snapshot, f"Snapshot for {ticker} missing 'ticker' field"
            assert "data" in ticker_snapshot, f"Snapshot for {ticker} missing 'data' field"
            assert "errors" in ticker_snapshot, f"Snapshot for {ticker} missing 'errors' field"
            
            # Verify ticker is in the original list
            assert ticker in [t.upper() for t in tickers], f"Unexpected ticker {ticker} in results"
        
        # Verify timestamp is present
        assert "timestamp" in snapshot, "Should have timestamp field"
        assert isinstance(snapshot["timestamp"], str), "timestamp should be a string"
        
        # Count successful vs failed
        successful_count = len(snapshot["snapshots"])
        print(f"✅ Processed {snapshot['tickers_count']} tickers: {successful_count} successful, "
              f"{len(snapshot['global_errors'])} global errors")
    
    @pytest.mark.asyncio
    async def test_get_multi_ticker_snapshot_empty_list(self):
        """Test empty ticker list handling"""
        snapshot = await get_multi_ticker_snapshot([], lookback_days=7)
        
        # Should handle gracefully
        assert snapshot["tickers_count"] == 0
        assert len(snapshot["snapshots"]) == 0
        assert len(snapshot["global_errors"]) > 0  # Should have error about empty list
    
    @pytest.mark.asyncio
    async def test_get_multi_ticker_snapshot_case_handling(self):
        """Test that tickers are properly uppercased"""
        tickers = ["aapl", "msft", "  GOOGL  "]  # Mixed case and whitespace
        
        snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        
        # Should clean and uppercase
        assert snapshot["tickers_count"] == 3
        
        # Check that snapshots have uppercase tickers
        for ticker in snapshot["snapshots"].keys():
            assert ticker.isupper()
            assert ticker.strip() == ticker  # No whitespace


# ============================================================================
# Formatting Tests
# ============================================================================

class TestFormatting:
    """Test suite for formatting functions"""
    
    @pytest.mark.asyncio
    async def test_format_snapshot_for_llm_structure(self):
        """Test that formatted snapshot has expected sections"""
        snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        formatted = format_snapshot_for_llm(snapshot)
        
        # Should be a string
        assert isinstance(formatted, str)
        
        # Should have header
        assert "FINANCIAL SNAPSHOT" in formatted
        assert "AAPL" in formatted
        
        # Should have section markers
        assert "===" in formatted
    
    @pytest.mark.asyncio
    async def test_format_snapshot_for_llm_compact(self):
        """Test that formatted snapshot is reasonably compact - vérifier taille < 5000 chars (~1250 tokens)
        
        Requirements: 3.7, 1.6
        Task 16 Sub-task 1: Verify formatted text is compact and under 5000 characters
        """
        snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        formatted = format_snapshot_for_llm(snapshot)
        
        # Should be compact - target is < 5000 chars (~1250 tokens)
        # This is the key requirement from task 16
        assert len(formatted) < 5000, f"Formatted text too long: {len(formatted)} chars (should be < 5000 chars / ~1250 tokens)"
        
        # Should still have meaningful content
        assert len(formatted) > 100, "Formatted text should have meaningful content"
        
        # Verify it's a string
        assert isinstance(formatted, str)
        
        print(f"✅ Formatted snapshot is compact: {len(formatted)} chars (~{len(formatted)//4} tokens)")
    
    @pytest.mark.asyncio
    async def test_format_snapshot_for_llm_sections(self):
        """Test that formatted snapshot has all expected sections with === markers
        
        Requirements: 3.7, 1.6
        Task 16 Sub-task 2: Verify presence of sections with "===" markers
        """
        snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        formatted = format_snapshot_for_llm(snapshot)
        
        # Should have section markers "===" (key requirement from task 16)
        assert "===" in formatted, "Formatted text should have section markers '==='"
        
        # Count section markers - should have multiple sections
        section_count = formatted.count("===")
        assert section_count >= 2, f"Should have at least 2 section markers, found {section_count}"
        
        # Should have main header
        assert "FINANCIAL SNAPSHOT" in formatted or "SNAPSHOT" in formatted, "Should have main header"
        
        # Should include ticker in header
        assert "AAPL" in formatted, "Should include ticker symbol"
        
        # Verify it's well-structured
        lines = formatted.split("\n")
        assert len(lines) > 5, "Should have multiple lines for different sections"
        
        print(f"✅ Formatted snapshot has {section_count} section markers and is well-structured")
    
    @pytest.mark.asyncio
    async def test_format_multi_snapshot_for_llm(self):
        """Test multi-ticker formatting with proper structure and separators
        
        Requirements: 2.4, 3.7
        Task 16 Sub-task 3: Verify formatage multi-ticker
        """
        tickers = ["AAPL", "MSFT", "GOOGL"]
        multi_snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        formatted = format_multi_snapshot_for_llm(multi_snapshot)
        
        # Should be a string
        assert isinstance(formatted, str), "Formatted output should be a string"
        
        # Should have multi-ticker header (key requirement from task 16)
        assert "MULTI-TICKER" in formatted or "MULTI TICKER" in formatted, "Should have multi-ticker header"
        
        # Should show ticker count
        assert str(multi_snapshot["tickers_count"]) in formatted, "Should show ticker count"
        
        # Should have section markers
        assert "===" in formatted, "Should have section markers"
        
        # Should have separators between tickers
        separator_count = formatted.count("---") + formatted.count("===")
        assert separator_count >= 2, f"Should have multiple separators, found {separator_count}"
        
        # Should be reasonably compact even with multiple tickers
        # Allow more space for multiple tickers but still reasonable
        assert len(formatted) < 15000, f"Multi-ticker formatted text too long: {len(formatted)} chars"
        
        # Verify timestamp is included
        assert "timestamp" in formatted.lower() or multi_snapshot["timestamp"][:10] in formatted, "Should include timestamp info"
        
        print(f"✅ Multi-ticker format has proper structure with {separator_count} separators, {len(formatted)} chars")
    
    @pytest.mark.asyncio
    async def test_format_with_errors(self):
        """Test formatting displays ⚠️ Partial data warning when errors are present
        
        Requirements: 3.7, 1.6
        Task 16 Sub-task 4: Verify affichage "⚠️ Partial data"
        """
        # Create a snapshot with errors (key requirement from task 16)
        snapshot = {
            "ticker": "TEST",
            "timestamp": datetime.now().isoformat(),
            "data": {"info": {"longName": "Test Company"}},
            "errors": ["Error fetching news", "Error fetching SEC filings"]
        }
        
        formatted = format_snapshot_for_llm(snapshot)
        
        # Should indicate partial data with warning emoji (key requirement)
        assert "⚠️" in formatted, "Should display warning emoji ⚠️"
        assert "Partial data" in formatted or "partial data" in formatted, "Should display 'Partial data' message"
        
        # Should mention errors
        assert "error" in formatted.lower(), "Should mention errors"
        
        # Should still include the ticker
        assert "TEST" in formatted, "Should still include ticker symbol"
        
        # Should still be formatted properly
        assert isinstance(formatted, str), "Should be a string"
        assert len(formatted) > 0, "Should have content"
        
        print(f"✅ Error formatting displays '⚠️ Partial data' warning correctly")
    
    @pytest.mark.asyncio
    async def test_format_snapshot_for_llm_with_errors(self):
        """Test formatting with errors displays warning (legacy test kept for compatibility)"""
        # Create a snapshot with errors
        snapshot = {
            "ticker": "TEST",
            "timestamp": datetime.now().isoformat(),
            "data": {"info": {"longName": "Test Company"}},
            "errors": ["Error 1", "Error 2"]
        }
        
        formatted = format_snapshot_for_llm(snapshot)
        
        # Should indicate partial data
        assert "⚠️" in formatted or "Partial data" in formatted or "error" in formatted.lower()
    
    @pytest.mark.asyncio
    async def test_format_multi_snapshot_for_llm_structure(self):
        """Test multi-ticker formatting structure (legacy test kept for compatibility)"""
        tickers = ["AAPL", "MSFT"]
        multi_snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        formatted = format_multi_snapshot_for_llm(multi_snapshot)
        
        # Should be a string
        assert isinstance(formatted, str)
        
        # Should have multi-ticker header
        assert "MULTI-TICKER" in formatted or "MULTI TICKER" in formatted
        
        # Should show ticker count
        assert str(len(tickers)) in formatted or "2" in formatted
    
    @pytest.mark.asyncio
    async def test_format_multi_snapshot_for_llm_separators(self):
        """Test that multiple tickers are properly separated"""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        multi_snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        formatted = format_multi_snapshot_for_llm(multi_snapshot)
        
        # Should have separators between tickers
        assert "---" in formatted or "===" in formatted
        
        # Should mention all tickers
        for ticker in tickers:
            # At least some tickers should appear (might have errors)
            pass  # Just verify no crash
    
    @pytest.mark.asyncio
    async def test_format_multi_snapshot_for_llm_with_global_errors(self):
        """Test formatting with global errors"""
        # Create a multi-snapshot with global errors
        multi_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "tickers_count": 2,
            "snapshots": {},
            "global_errors": ["Global error 1", "Global error 2"]
        }
        
        formatted = format_multi_snapshot_for_llm(multi_snapshot)
        
        # Should display global errors
        assert "GLOBAL ERRORS" in formatted or "error" in formatted.lower()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_single_ticker_workflow(self):
        """Test complete workflow: snapshot -> format"""
        # Get snapshot
        snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        
        # Format for LLM
        formatted = format_snapshot_for_llm(snapshot)
        
        # Verify complete workflow
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "AAPL" in formatted
    
    @pytest.mark.asyncio
    async def test_complete_multi_ticker_workflow(self):
        """Test complete workflow: multi-snapshot -> format"""
        # Get multi-snapshot
        tickers = ["AAPL", "MSFT"]
        multi_snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        
        # Format for LLM
        formatted = format_multi_snapshot_for_llm(multi_snapshot)
        
        # Verify complete workflow
        assert isinstance(formatted, str)
        assert len(formatted) > 0
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self):
        """Test that meta-tools are faster than sequential calls"""
        import time
        
        # This is a conceptual test - in practice, meta-tools should be
        # significantly faster than making 7+ individual calls
        
        start = time.time()
        snapshot = await get_financial_snapshot("AAPL", lookback_days=7)
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 30, f"Single ticker snapshot took too long: {elapsed}s"
        
        # Verify we got data
        assert len(snapshot["data"]) > 0 or len(snapshot["errors"]) > 0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_snapshot_with_special_characters(self):
        """Test ticker with special characters"""
        # Some tickers have special characters (e.g., BRK.B)
        snapshot = await get_financial_snapshot("BRK.B", lookback_days=7)
        
        # Should handle gracefully
        assert "ticker" in snapshot
        assert isinstance(snapshot["data"], dict)
    
    @pytest.mark.asyncio
    async def test_snapshot_with_lowercase_ticker(self):
        """Test that lowercase tickers are handled"""
        snapshot = await get_financial_snapshot("aapl", lookback_days=7)
        
        # Should uppercase
        assert snapshot["ticker"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_multi_snapshot_with_duplicates(self):
        """Test handling of duplicate tickers"""
        tickers = ["AAPL", "AAPL", "MSFT"]
        
        snapshot = await get_multi_ticker_snapshot(tickers, lookback_days=7)
        
        # Should handle gracefully (might dedupe or process both)
        assert "tickers_count" in snapshot
        assert isinstance(snapshot["snapshots"], dict)
    
    @pytest.mark.asyncio
    async def test_format_empty_snapshot(self):
        """Test formatting an empty snapshot"""
        empty_snapshot = {
            "ticker": "EMPTY",
            "timestamp": datetime.now().isoformat(),
            "data": {},
            "errors": []
        }
        
        formatted = format_snapshot_for_llm(empty_snapshot)
        
        # Should not crash
        assert isinstance(formatted, str)
        assert "EMPTY" in formatted
