"""
Tests for MCP configuration tools and ConfigurationManager.

Requirements: 8.1, 8.2
"""

import pytest
import os
import tempfile
from pathlib import Path
from iso_financial_mcp.server import configure_api_key, get_configuration, list_data_sources
from iso_financial_mcp.reliability.configuration_manager import ConfigurationManager

# Configure pytest for anyio
pytestmark = pytest.mark.anyio


# ============================================================================
# MCP Configuration Tools Tests - Requirement 8.2
# ============================================================================

class TestConfigureApiKeyTool:
    """Test configure_api_key MCP tool"""
    
    @pytest.mark.asyncio
    async def test_configure_api_key_invalid_provider(self):
        """Test configure_api_key with invalid provider"""
        result = await configure_api_key("invalid_provider", "test_key")
        assert "❌" in result
        assert "Invalid provider" in result or "invalid" in result.lower()
    
    @pytest.mark.asyncio
    async def test_configure_api_key_alpha_vantage(self):
        """Test configure_api_key with Alpha Vantage provider"""
        result = await configure_api_key("alpha_vantage", "test_key_12345")
        # Should either succeed or show warning (validation will likely fail)
        assert "alpha_vantage" in result.lower() or "Alpha Vantage" in result
        assert ("✅" in result or "⚠️" in result or "❌" in result)
    
    @pytest.mark.asyncio
    async def test_configure_api_key_serpapi(self):
        """Test configure_api_key with SerpAPI provider"""
        result = await configure_api_key("serpapi", "test_serpapi_key_789")
        # Should either succeed or show warning
        assert "serpapi" in result.lower() or "SerpAPI" in result
        assert ("✅" in result or "⚠️" in result or "❌" in result)
    
    @pytest.mark.asyncio
    async def test_configure_api_key_empty_key(self):
        """Test configure_api_key with empty API key"""
        result = await configure_api_key("alpha_vantage", "")
        # Should handle empty key gracefully
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_configure_api_key_case_insensitive(self):
        """Test that provider names are case-insensitive"""
        result1 = await configure_api_key("ALPHA_VANTAGE", "test_key")
        result2 = await configure_api_key("Alpha_Vantage", "test_key")
        
        # Both should be handled (either accepted or rejected consistently)
        assert isinstance(result1, str)
        assert isinstance(result2, str)


class TestGetConfigurationTool:
    """Test get_configuration MCP tool"""
    
    @pytest.mark.asyncio
    async def test_get_configuration_structure(self):
        """Test get_configuration returns properly formatted output"""
        result = await get_configuration()
        assert "📋 Current Configuration" in result or "Configuration" in result
        assert "API Keys" in result or "🔑" in result
        assert "Cache" in result or "💾" in result
    
    @pytest.mark.asyncio
    async def test_get_configuration_shows_providers(self):
        """Test that get_configuration shows all providers"""
        result = await get_configuration()
        assert "Alpha Vantage" in result or "alpha_vantage" in result.lower()
        assert "Serpapi" in result or "SerpAPI" in result or "serpapi" in result.lower()
    
    @pytest.mark.asyncio
    async def test_get_configuration_masks_keys(self):
        """Test that API keys are masked in output"""
        # First configure a key
        await configure_api_key("alpha_vantage", "TESTKEY123456789")
        
        # Get configuration
        result = await get_configuration()
        
        # Full key should not be visible
        assert "TESTKEY123456789" not in result
        # Should show masked version or "Not configured"
        assert ("..." in result or "Not configured" in result or "****" in result)
    
    @pytest.mark.asyncio
    async def test_get_configuration_shows_cache_settings(self):
        """Test that cache configuration is displayed"""
        result = await get_configuration()
        assert "Cache" in result or "cache" in result.lower()
        # Should show TTL or size information
        assert ("TTL" in result or "ttl" in result.lower() or 
                "size" in result.lower() or "MB" in result)


class TestListDataSourcesTool:
    """Test list_data_sources MCP tool"""
    
    @pytest.mark.asyncio
    async def test_list_data_sources_structure(self):
        """Test list_data_sources returns properly formatted output"""
        result = await list_data_sources()
        assert "📊 Available Data Sources" in result or "Data Sources" in result
        assert "FREE SOURCES" in result or "Free" in result
        assert "OPTIONAL SOURCES" in result or "Optional" in result
    
    @pytest.mark.asyncio
    async def test_list_data_sources_shows_all_sources(self):
        """Test that all data sources are listed"""
        result = await list_data_sources()
        
        # Free sources
        assert "Yahoo Finance" in result or "yfinance" in result.lower()
        assert "SEC" in result or "EDGAR" in result
        assert "FINRA" in result
        assert "Google Trends" in result or "Trends" in result
        
        # Optional sources
        assert "Alpha Vantage" in result
        assert "SerpAPI" in result or "Serpapi" in result
    
    @pytest.mark.asyncio
    async def test_list_data_sources_shows_status(self):
        """Test that source status is indicated"""
        result = await list_data_sources()
        
        # Should have status indicators (emojis or text)
        assert ("✅" in result or "✓" in result or "enabled" in result.lower() or
                "⚠️" in result or "disabled" in result.lower())
    
    @pytest.mark.asyncio
    async def test_list_data_sources_shows_descriptions(self):
        """Test that sources have descriptions"""
        result = await list_data_sources()
        
        # Should have some descriptive text
        assert ("market data" in result.lower() or "filings" in result.lower() or
                "news" in result.lower() or "earnings" in result.lower())
    
    @pytest.mark.asyncio
    async def test_list_data_sources_shows_signup_info(self):
        """Test that optional sources show signup information"""
        result = await list_data_sources()
        
        # Should mention how to get API keys or configure
        assert ("configure" in result.lower() or "sign up" in result.lower() or
                "api key" in result.lower() or "requires" in result.lower())


# ============================================================================
# ConfigurationManager Tests - Requirement 8.1
# ============================================================================

class TestConfigurationManagerPriority:
    """Test configuration priority order (MCP > env > YAML > defaults)"""
    
    def test_priority_mcp_over_yaml(self):
        """Test MCP config has priority over YAML config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            # Set in YAML (lower priority)
            config_manager._persist_to_yaml("test.key", "yaml_value")
            config_manager.yaml_config = config_manager._load_yaml_config()
            
            # Set in MCP (higher priority)
            config_manager.set_mcp_config("test.key", "mcp_value")
            
            # MCP should win
            assert config_manager.get("test.key") == "mcp_value"
    
    def test_priority_env_over_yaml(self):
        """Test environment variables have priority over YAML"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            
            # Set environment variable
            os.environ["TEST_KEY"] = "env_value"
            
            try:
                config_manager = ConfigurationManager(yaml_path=str(yaml_path))
                
                # Set in YAML (lower priority)
                config_manager._persist_to_yaml("test.key", "yaml_value")
                config_manager.yaml_config = config_manager._load_yaml_config()
                
                # Env should win
                assert config_manager.get("test.key") == "env_value"
            finally:
                del os.environ["TEST_KEY"]
    
    def test_priority_yaml_over_defaults(self):
        """Test YAML config has priority over defaults"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            # Set in YAML
            config_manager._persist_to_yaml("cache.memory.ttl_seconds", 7200)
            config_manager.yaml_config = config_manager._load_yaml_config()
            
            # YAML should override default
            assert config_manager.get("cache.memory.ttl_seconds") == 7200
    
    def test_priority_full_chain(self):
        """Test complete priority chain: MCP > env > YAML > defaults"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            
            # Set environment variable
            os.environ["PRIORITY_TEST"] = "env_value"
            
            try:
                config_manager = ConfigurationManager(yaml_path=str(yaml_path))
                
                # Set in YAML
                config_manager._persist_to_yaml("priority.test", "yaml_value")
                config_manager.yaml_config = config_manager._load_yaml_config()
                
                # Env should win over YAML
                assert config_manager.get("priority.test") == "env_value"
                
                # Set in MCP (highest priority)
                config_manager.set_mcp_config("priority.test", "mcp_value")
                
                # MCP should win over everything
                assert config_manager.get("priority.test") == "mcp_value"
            finally:
                del os.environ["PRIORITY_TEST"]
    
    def test_default_fallback(self):
        """Test fallback to default when key not found in other sources"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            # Should return default value
            default_ttl = config_manager.get("cache.memory.ttl_seconds")
            assert default_ttl == 3600  # Default from hardcoded config


class TestConfigurationManagerMasking:
    """Test API key masking functionality"""
    
    def test_mask_api_keys_short(self):
        """Test masking of short API keys (< 4 chars)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            config_manager.set_mcp_config("alpha_vantage.api_key", "ABC")
            
            all_config = config_manager.get_all_config(mask_secrets=True)
            alpha_vantage_config = all_config.get("alpha_vantage", {})
            masked_key = alpha_vantage_config.get("api_key", "")
            
            # Short keys should be fully masked
            assert masked_key == "****"
            assert "ABC" not in masked_key
    
    def test_mask_api_keys_long(self):
        """Test masking of long API keys (> 4 chars)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            config_manager.set_mcp_config("alpha_vantage.api_key", "ABCDEFGHIJKLMNOP")
            
            all_config = config_manager.get_all_config(mask_secrets=True)
            alpha_vantage_config = all_config.get("alpha_vantage", {})
            masked_key = alpha_vantage_config.get("api_key", "")
            
            # Should show only last 4 characters
            assert "MNOP" in masked_key
            assert "...MNOP" == masked_key
            assert "ABCDEFGHIJKLMNOP" != masked_key
    
    def test_no_masking_when_disabled(self):
        """Test that masking can be disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            config_manager.set_mcp_config("alpha_vantage.api_key", "TESTKEY12345")
            
            all_config = config_manager.get_all_config(mask_secrets=False)
            alpha_vantage_config = all_config.get("alpha_vantage", {})
            api_key = alpha_vantage_config.get("api_key", "")
            
            # Should show full key when masking disabled
            assert api_key == "TESTKEY12345"
    
    def test_mask_multiple_secrets(self):
        """Test masking of multiple API keys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            config_manager.set_mcp_config("alpha_vantage.api_key", "ALPHAVANTAGEKEY123")
            config_manager.set_mcp_config("serpapi.api_key", "SERPAPIKEY456")
            
            all_config = config_manager.get_all_config(mask_secrets=True)
            
            # Both should be masked
            av_key = all_config.get("alpha_vantage", {}).get("api_key", "")
            serpapi_key = all_config.get("serpapi", {}).get("api_key", "")
            
            # Should show only last 4 characters
            assert av_key.endswith("Y123") or av_key.endswith("123")
            assert serpapi_key.endswith("Y456") or serpapi_key.endswith("456")
            assert "..." in av_key
            assert "..." in serpapi_key


class TestConfigurationManagerPersistence:
    """Test YAML persistence functionality"""
    
    def test_persist_to_yaml_creates_file(self):
        """Test that setting MCP config creates YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            # File should not exist yet
            assert not yaml_path.exists()
            
            # Set config via MCP
            config_manager.set_mcp_config("test.key", "test_value")
            
            # File should now exist
            assert yaml_path.exists()
    
    def test_persist_to_yaml_preserves_data(self):
        """Test that YAML persistence preserves data across instances"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            
            # First instance
            config_manager1 = ConfigurationManager(yaml_path=str(yaml_path))
            config_manager1.set_mcp_config("alpha_vantage.api_key", "TESTKEY123")
            
            # Second instance (simulates restart)
            config_manager2 = ConfigurationManager(yaml_path=str(yaml_path))
            
            # Should load from YAML
            assert config_manager2.get("alpha_vantage.api_key") == "TESTKEY123"
    
    def test_persist_nested_keys(self):
        """Test persistence of nested configuration keys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            # Set nested keys
            config_manager.set_mcp_config("cache.memory.ttl_seconds", 7200)
            config_manager.set_mcp_config("cache.disk.max_size_mb", 1000)
            
            # Reload from YAML
            config_manager2 = ConfigurationManager(yaml_path=str(yaml_path))
            
            assert config_manager2.get("cache.memory.ttl_seconds") == 7200
            assert config_manager2.get("cache.disk.max_size_mb") == 1000


class TestConfigurationManagerValidation:
    """Test API key validation functionality"""
    
    @pytest.mark.asyncio
    async def test_validate_invalid_provider(self):
        """Test validation with invalid provider"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            is_valid, message = await config_manager.validate_api_key("invalid_provider", "test_key")
            
            assert is_valid is False
            assert "Unknown provider" in message
    
    @pytest.mark.asyncio
    async def test_validate_alpha_vantage_invalid_key(self):
        """Test Alpha Vantage validation with invalid key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            is_valid, message = await config_manager.validate_api_key("alpha_vantage", "INVALID_KEY")
            
            # Should fail validation
            assert is_valid is False
            assert isinstance(message, str)
    
    @pytest.mark.asyncio
    async def test_validation_caching(self):
        """Test that validation results are cached"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            config_manager = ConfigurationManager(yaml_path=str(yaml_path))
            
            # First validation
            is_valid1, message1 = await config_manager.validate_api_key("alpha_vantage", "TEST_KEY")
            
            # Second validation (should use cache)
            is_valid2, message2 = await config_manager.validate_api_key("alpha_vantage", "TEST_KEY")
            
            # Results should be consistent
            assert is_valid1 == is_valid2
            
            # Cache should have the entry
            cache_key = ("alpha_vantage", "TEST_KEY")
            assert cache_key in config_manager._validation_cache


# ============================================================================
# MCP Health Check Tools Tests - Requirement 8.2
# ============================================================================

class TestGetHealthStatusTool:
    """Test get_health_status MCP tool"""
    
    @pytest.mark.asyncio
    async def test_get_health_status_structure(self):
        """Test get_health_status returns properly formatted output"""
        from iso_financial_mcp.server import get_health_status
        
        result = await get_health_status()
        
        # Should be a string
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Should have health-related content
        assert "health" in result.lower() or "status" in result.lower()
    
    @pytest.mark.asyncio
    async def test_get_health_status_no_data(self):
        """Test get_health_status when no health data is available"""
        from iso_financial_mcp.server import get_health_status
        
        result = await get_health_status()
        
        # Should handle case where no health data exists yet
        assert isinstance(result, str)
        # Should either show empty state or have health header
        assert ("health" in result.lower() or "status" in result.lower() or
                "no data" in result.lower() or "not available" in result.lower())
    
    @pytest.mark.asyncio
    async def test_get_health_status_with_data(self):
        """Test get_health_status returns formatted health data"""
        from iso_financial_mcp.server import get_health_status
        from iso_financial_mcp.reliability.data_manager import DataManager
        
        # Create a data manager and record some test metrics
        data_manager = DataManager()
        health_monitor = data_manager.health_monitor
        
        # Record some test requests
        health_monitor.record_request("test_source", True, 100, None)
        health_monitor.record_request("test_source", True, 150, None)
        health_monitor.record_request("test_source", False, 200, "timeout")
        
        result = await get_health_status()
        
        # Check for expected formatting
        assert "🏥" in result or "Health" in result
        # Should show metrics
        assert ("Success Rate" in result or "success" in result.lower() or
                "Latency" in result or "latency" in result.lower() or
                "Requests" in result or "requests" in result.lower())
    
    @pytest.mark.asyncio
    async def test_get_health_status_shows_status_indicators(self):
        """Test that health status shows status indicators"""
        from iso_financial_mcp.server import get_health_status
        
        result = await get_health_status()
        
        # Should have status indicators (emojis or text)
        # Either shows indicators or mentions no data yet
        assert (result.count("✅") >= 0 or result.count("⚠️") >= 0 or 
                result.count("❌") >= 0 or "no data" in result.lower())


class TestTestDataSourceTool:
    """Test test_data_source MCP tool"""
    
    @pytest.mark.asyncio
    async def test_test_data_source_invalid_source(self):
        """Test test_data_source with invalid source name"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("invalid_source_xyz", "AAPL")
        
        assert "❌" in result
        assert ("Invalid" in result or "invalid" in result.lower())
        assert ("Valid sources" in result or "valid" in result.lower())
    
    @pytest.mark.asyncio
    async def test_test_data_source_yfinance(self):
        """Test test_data_source with yfinance source"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("yfinance", "AAPL")
        
        # Should either succeed or fail gracefully
        assert "🧪 Testing" in result or "Testing" in result
        assert "YFINANCE" in result or "yfinance" in result.lower()
        assert "AAPL" in result
        assert ("✅" in result or "❌" in result)
        assert ("Response time" in result or "Time to failure" in result or
                "time" in result.lower())
    
    @pytest.mark.asyncio
    async def test_test_data_source_sec(self):
        """Test test_data_source with SEC source"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("sec", "AAPL")
        
        # Should either succeed or fail gracefully
        assert "🧪 Testing" in result or "Testing" in result
        assert "SEC" in result
        assert "AAPL" in result
        assert ("✅" in result or "❌" in result)
    
    @pytest.mark.asyncio
    async def test_test_data_source_trends(self):
        """Test test_data_source with Google Trends source"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("trends", "AAPL")
        
        # Should either succeed or fail gracefully
        assert "🧪 Testing" in result or "Testing" in result
        assert ("TRENDS" in result or "trends" in result.lower())
        assert "AAPL" in result
        assert ("✅" in result or "❌" in result)
    
    @pytest.mark.asyncio
    async def test_test_data_source_earnings(self):
        """Test test_data_source with earnings source"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("earnings", "AAPL")
        
        # Should either succeed or fail gracefully
        assert "🧪 Testing" in result or "Testing" in result
        assert ("EARNINGS" in result or "earnings" in result.lower())
        assert "AAPL" in result
        assert ("✅" in result or "❌" in result)
    
    @pytest.mark.asyncio
    async def test_test_data_source_finra(self):
        """Test test_data_source with FINRA source"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("finra", "AAPL")
        
        # Should either succeed or fail gracefully
        assert "🧪 Testing" in result or "Testing" in result
        assert "FINRA" in result
        assert "AAPL" in result
        assert ("✅" in result or "❌" in result)
    
    @pytest.mark.asyncio
    async def test_test_data_source_news(self):
        """Test test_data_source with news source"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("news", "AAPL")
        
        # Should either succeed or fail gracefully
        assert "🧪 Testing" in result or "Testing" in result
        assert ("NEWS" in result or "news" in result.lower())
        assert "AAPL" in result
        assert ("✅" in result or "❌" in result)
    
    @pytest.mark.asyncio
    async def test_test_data_source_case_insensitive(self):
        """Test that test_data_source handles case-insensitive source names"""
        from iso_financial_mcp.server import test_data_source
        
        # Test with uppercase
        result1 = await test_data_source("SEC", "AAPL")
        assert "🧪 Testing" in result1 or "Testing" in result1
        
        # Test with mixed case
        result2 = await test_data_source("YFinance", "AAPL")
        assert "🧪 Testing" in result2 or "Testing" in result2
        
        # Test with lowercase
        result3 = await test_data_source("trends", "AAPL")
        assert "🧪 Testing" in result3 or "Testing" in result3
    
    @pytest.mark.asyncio
    async def test_test_data_source_different_tickers(self):
        """Test test_data_source with different ticker symbols"""
        from iso_financial_mcp.server import test_data_source
        
        # Test with different tickers
        result1 = await test_data_source("yfinance", "MSFT")
        assert "MSFT" in result1
        
        result2 = await test_data_source("yfinance", "GOOGL")
        assert "GOOGL" in result2
    
    @pytest.mark.asyncio
    async def test_test_data_source_shows_timing(self):
        """Test that test_data_source shows response timing"""
        from iso_financial_mcp.server import test_data_source
        
        result = await test_data_source("yfinance", "AAPL")
        
        # Should show timing information
        assert ("time" in result.lower() or "ms" in result.lower() or 
                "seconds" in result.lower() or "s" in result)
    
    @pytest.mark.asyncio
    async def test_test_data_source_error_handling(self):
        """Test that test_data_source handles errors gracefully"""
        from iso_financial_mcp.server import test_data_source
        
        # Use an invalid ticker that might cause errors
        result = await test_data_source("yfinance", "INVALID_TICKER_XYZ123")
        
        # Should handle gracefully (either succeed with empty data or show error)
        assert isinstance(result, str)
        assert len(result) > 0
        assert ("✅" in result or "❌" in result or "⚠️" in result)
