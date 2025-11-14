"""
Tests for refactoring verification.

Verifies that:
- No duplicate files exist in datasources
- No MD files exist in reliability/
- All imports work correctly

Requirements: 8.1, 8.3
"""

import pytest
from pathlib import Path


class TestNoDuplicateFiles:
    """Test that no duplicate files exist in datasources - Requirement 8.1"""
    
    def test_no_earnings_sources_duplicate(self):
        """Test that earnings_sources.py (duplicate) does not exist"""
        datasources_dir = Path("iso_financial_mcp/datasources")
        duplicate_file = datasources_dir / "earnings_sources.py"
        
        assert not duplicate_file.exists(), \
            "Duplicate file earnings_sources.py should not exist (should use earnings_source_manager.py)"
    
    def test_no_trends_sources_duplicate(self):
        """Test that trends_sources.py (duplicate) does not exist"""
        datasources_dir = Path("iso_financial_mcp/datasources")
        duplicate_file = datasources_dir / "trends_sources.py"
        
        assert not duplicate_file.exists(), \
            "Duplicate file trends_sources.py should not exist (should use trends_source_manager.py)"
    
    def test_earnings_source_manager_exists(self):
        """Test that earnings_source_manager.py exists"""
        datasources_dir = Path("iso_financial_mcp/datasources")
        manager_file = datasources_dir / "earnings_source_manager.py"
        
        assert manager_file.exists(), \
            "earnings_source_manager.py should exist as the consolidated file"
    
    def test_trends_source_manager_exists(self):
        """Test that trends_source_manager.py exists"""
        datasources_dir = Path("iso_financial_mcp/datasources")
        manager_file = datasources_dir / "trends_source_manager.py"
        
        assert manager_file.exists(), \
            "trends_source_manager.py should exist as the consolidated file"
    
    def test_sec_source_manager_exists(self):
        """Test that sec_source_manager.py exists"""
        datasources_dir = Path("iso_financial_mcp/datasources")
        manager_file = datasources_dir / "sec_source_manager.py"
        
        assert manager_file.exists(), \
            "sec_source_manager.py should exist"
    
    def test_datasources_structure(self):
        """Test that datasources directory has expected structure"""
        datasources_dir = Path("iso_financial_mcp/datasources")
        
        # Expected files
        expected_files = [
            "__init__.py",
            "yfinance_source.py",
            "sec_source.py",
            "sec_source_manager.py",
            "sec_rss_source.py",
            "sec_xbrl_source.py",
            "finra_source.py",
            "earnings_source.py",
            "earnings_source_manager.py",
            "news_source.py",
            "trends_source.py",
            "trends_source_manager.py",
            "validation.py"
        ]
        
        for filename in expected_files:
            file_path = datasources_dir / filename
            assert file_path.exists(), f"Expected file {filename} should exist"
        
        # Files that should NOT exist
        forbidden_files = [
            "earnings_sources.py",  # Duplicate
            "trends_sources.py"     # Duplicate
        ]
        
        for filename in forbidden_files:
            file_path = datasources_dir / filename
            assert not file_path.exists(), f"Duplicate file {filename} should not exist"


class TestNoMDInReliability:
    """Test that no MD files exist in reliability/ - Requirement 8.3"""
    
    def test_no_md_files_in_reliability(self):
        """Test that reliability/ directory contains no .md files"""
        reliability_dir = Path("iso_financial_mcp/reliability")
        md_files = list(reliability_dir.glob("*.md"))
        
        assert len(md_files) == 0, \
            f"Found {len(md_files)} MD files in reliability/: {[f.name for f in md_files]}. " \
            "All documentation should be in docs/ or .kiro/specs/"
    
    def test_reliability_has_only_code_and_config(self):
        """Test that reliability/ contains only Python files and YAML config"""
        reliability_dir = Path("iso_financial_mcp/reliability")
        
        # Get all files (excluding __pycache__)
        all_files = [f for f in reliability_dir.iterdir() 
                    if f.is_file() and not f.name.startswith('.')]
        
        # Check each file has allowed extension
        allowed_extensions = {'.py', '.yaml', '.yml'}
        
        for file_path in all_files:
            assert file_path.suffix in allowed_extensions, \
                f"File {file_path.name} has unexpected extension {file_path.suffix}. " \
                f"Only {allowed_extensions} are allowed in reliability/"
    
    def test_default_config_yaml_exists(self):
        """Test that default_config.yaml exists in reliability/"""
        reliability_dir = Path("iso_financial_mcp/reliability")
        config_file = reliability_dir / "default_config.yaml"
        
        assert config_file.exists(), \
            "default_config.yaml should exist in reliability/"


class TestImportsFunctional:
    """Test that all imports work correctly after refactoring"""
    
    def test_import_datasources_package(self):
        """Test that datasources package can be imported"""
        try:
            import iso_financial_mcp.datasources
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import datasources package: {e}")
    
    def test_import_yfinance_source(self):
        """Test that yfinance_source can be imported"""
        try:
            from iso_financial_mcp.datasources import yfinance_source
            assert yfinance_source is not None
        except ImportError as e:
            pytest.fail(f"Failed to import yfinance_source: {e}")
    
    def test_import_sec_source_manager(self):
        """Test that sec_source_manager can be imported"""
        try:
            from iso_financial_mcp.datasources import sec_source_manager
            assert sec_source_manager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import sec_source_manager: {e}")
    
    def test_import_earnings_source_manager(self):
        """Test that earnings_source_manager can be imported"""
        try:
            from iso_financial_mcp.datasources import earnings_source_manager
            assert earnings_source_manager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import earnings_source_manager: {e}")
    
    def test_import_trends_source_manager(self):
        """Test that trends_source_manager can be imported"""
        try:
            from iso_financial_mcp.datasources import trends_source_manager
            assert trends_source_manager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import trends_source_manager: {e}")
    
    def test_import_finra_source(self):
        """Test that finra_source can be imported"""
        try:
            from iso_financial_mcp.datasources import finra_source
            assert finra_source is not None
        except ImportError as e:
            pytest.fail(f"Failed to import finra_source: {e}")
    
    def test_import_news_source(self):
        """Test that news_source can be imported"""
        try:
            from iso_financial_mcp.datasources import news_source
            assert news_source is not None
        except ImportError as e:
            pytest.fail(f"Failed to import news_source: {e}")
    
    def test_import_validation(self):
        """Test that validation module can be imported"""
        try:
            from iso_financial_mcp.datasources import validation
            assert validation is not None
        except ImportError as e:
            pytest.fail(f"Failed to import validation: {e}")
    
    def test_import_server(self):
        """Test that server module can be imported"""
        try:
            from iso_financial_mcp import server
            assert server is not None
        except ImportError as e:
            pytest.fail(f"Failed to import server: {e}")
    
    def test_import_meta_tools(self):
        """Test that meta_tools module can be imported"""
        try:
            from iso_financial_mcp import meta_tools
            assert meta_tools is not None
        except ImportError as e:
            pytest.fail(f"Failed to import meta_tools: {e}")
    
    def test_import_reliability_modules(self):
        """Test that reliability modules can be imported"""
        try:
            from iso_financial_mcp.reliability import configuration_manager
            from iso_financial_mcp.reliability import cache_layer
            from iso_financial_mcp.reliability import health_monitor
            from iso_financial_mcp.reliability import data_manager
            
            assert configuration_manager is not None
            assert cache_layer is not None
            assert health_monitor is not None
            assert data_manager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import reliability modules: {e}")
    
    def test_no_import_of_duplicate_files(self):
        """Test that duplicate files cannot be imported"""
        # These imports should fail because files don't exist
        with pytest.raises(ImportError):
            from iso_financial_mcp.datasources import earnings_sources
        
        with pytest.raises(ImportError):
            from iso_financial_mcp.datasources import trends_sources


class TestServerStartup:
    """Test that server can be initialized without errors"""
    
    def test_server_module_loads(self):
        """Test that server module loads without errors"""
        try:
            # Import the server variable from the module
            from iso_financial_mcp.server import server
            # Check that it's a FastMCP instance
            from fastmcp.server.server import FastMCP
            assert isinstance(server, FastMCP)
            assert server.name == "IsoFinancial-MCP"
        except Exception as e:
            pytest.fail(f"Failed to load server module: {e}")
    
    def test_configuration_manager_initializes(self):
        """Test that ConfigurationManager can be initialized"""
        try:
            from iso_financial_mcp.reliability.configuration_manager import ConfigurationManager
            config_manager = ConfigurationManager()
            assert config_manager is not None
        except Exception as e:
            pytest.fail(f"Failed to initialize ConfigurationManager: {e}")
    
    def test_meta_tools_functions_exist(self):
        """Test that meta-tools functions exist and are callable"""
        try:
            from iso_financial_mcp.meta_tools import (
                get_financial_snapshot,
                get_multi_ticker_snapshot,
                format_snapshot_for_llm,
                format_multi_snapshot_for_llm
            )
            
            assert callable(get_financial_snapshot)
            assert callable(get_multi_ticker_snapshot)
            assert callable(format_snapshot_for_llm)
            assert callable(format_multi_snapshot_for_llm)
        except Exception as e:
            pytest.fail(f"Failed to import meta-tools functions: {e}")


class TestDocumentationStructure:
    """Test that documentation is properly organized"""
    
    def test_docs_directory_exists(self):
        """Test that docs/ directory exists"""
        docs_dir = Path("docs")
        assert docs_dir.exists(), "docs/ directory should exist"
        assert docs_dir.is_dir(), "docs/ should be a directory"
    
    def test_architecture_doc_exists(self):
        """Test that ARCHITECTURE.md exists in docs/"""
        arch_doc = Path("docs/ARCHITECTURE.md")
        assert arch_doc.exists(), "docs/ARCHITECTURE.md should exist"
    
    def test_configuration_doc_exists(self):
        """Test that CONFIGURATION.md exists in docs/"""
        config_doc = Path("docs/CONFIGURATION.md")
        assert config_doc.exists(), "docs/CONFIGURATION.md should exist"
    
    def test_reliability_doc_exists(self):
        """Test that RELIABILITY.md exists in docs/"""
        reliability_doc = Path("docs/RELIABILITY.md")
        assert reliability_doc.exists(), "docs/RELIABILITY.md should exist"
    
    def test_root_docs_exist(self):
        """Test that root documentation files exist"""
        readme = Path("README.md")
        changelog = Path("CHANGELOG.md")
        license_file = Path("LICENSE")
        
        assert readme.exists(), "README.md should exist at root"
        assert changelog.exists(), "CHANGELOG.md should exist at root"
        assert license_file.exists(), "LICENSE should exist at root"
