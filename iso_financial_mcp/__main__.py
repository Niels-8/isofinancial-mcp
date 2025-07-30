#!/usr/bin/env python3
"""
Entry point for IsoFinancial-MCP package execution.
Allows running the package with: python -m iso_financial_mcp
"""

from .server import server

if __name__ == "__main__":
    print("🚀 Starting IsoFinancial-MCP Server")
    print("✅ Using Yahoo Finance data sources")
    print("📡 Server ready for MCP connections")
    print("🔗 Got to https://github.com/Niels-8/isofinancial-mcp for more information")
    print("⭐️ If you like this library give it a star on github, thank you !")
    server.run() 