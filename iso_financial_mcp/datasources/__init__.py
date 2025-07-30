"""
IsoFinancial-MCP Data Sources Package

This package contains data source modules for the IsoFinancial-MCP server.
Currently includes Yahoo Finance integration for market data.
"""

__version__ = "0.1.0"
__author__ = "Niels-8"

from . import yfinance_source

__all__ = ["yfinance_source"] 