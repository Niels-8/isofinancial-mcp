#!/usr/bin/env python3
"""
Entry point for IsoFinancial-MCP package execution.
Allows running the package with: python -m iso_financial_mcp
"""

from . import __version__
from .server import server


def format_welcome_message() -> str:
    """
    Format a professional welcome message for the IsoFinancial-MCP server.
    
    Returns:
        Formatted welcome message with version, available sources, and basic instructions.
    """
    lines = []
    
    # Header
    lines.append("=" * 70)
    lines.append(f"🚀 IsoFinancial-MCP Server v{__version__}")
    lines.append("=" * 70)
    lines.append("")
    
    # Available data sources
    lines.append("📊 AVAILABLE DATA SOURCES:")
    lines.append("")
    lines.append("  ✅ Yahoo Finance - Market data, prices, options, financials")
    lines.append("  ✅ SEC EDGAR - SEC filings (8-K, 10-Q, 10-K, S-3, 424B)")
    lines.append("  ✅ FINRA - Daily short volume data with ratios")
    lines.append("  ✅ Google Trends - Search volume analysis")
    lines.append("  ✅ News (RSS) - Recent headlines from multiple sources")
    lines.append("  ✅ Earnings Calendar - EPS estimates and actuals")
    lines.append("")
    lines.append("  🔑 OPTIONAL (API Key Required):")
    lines.append("     • Alpha Vantage - Additional earnings data")
    lines.append("     • SerpAPI - Google Trends fallback")
    lines.append("")
    
    # Meta-tools highlight
    lines.append("🎯 META-TOOLS (Recommended):")
    lines.append("")
    lines.append("  • get_ticker_complete_analysis() - All data in 1 call")
    lines.append("  • get_multi_ticker_analysis() - Multiple tickers in parallel")
    lines.append("  • analyze_sector_companies() - Sector analysis workflow")
    lines.append("")
    
    # Configuration tools
    lines.append("⚙️  CONFIGURATION & DIAGNOSTICS:")
    lines.append("")
    lines.append("  • configure_api_key() - Set API keys via MCP")
    lines.append("  • list_data_sources() - View all available sources")
    lines.append("  • get_health_status() - Check source health")
    lines.append("  • test_data_source() - Test a specific source")
    lines.append("")
    
    # Basic instructions
    lines.append("💡 GETTING STARTED:")
    lines.append("")
    lines.append("  1. Use meta-tools for efficient multi-source data retrieval")
    lines.append("  2. Configure optional API keys with configure_api_key()")
    lines.append("  3. Check source status with list_data_sources()")
    lines.append("  4. All data sources are free/public (no API keys required)")
    lines.append("")
    
    # Footer
    lines.append("📖 Documentation: https://github.com/Niels-8/isofinancial-mcp")
    lines.append("⭐ Star us on GitHub if you find this useful!")
    lines.append("=" * 70)
    lines.append("")
    lines.append("📡 Server ready for MCP connections...")
    lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_welcome_message())
    server.run() 