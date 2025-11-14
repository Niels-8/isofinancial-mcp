"""
IsoFinancial-MCP Data Sources Package

This package contains data source modules for the IsoFinancial-MCP server.
Currently includes Yahoo Finance integration for market data.
"""

__version__ = "0.1.0"
__author__ = "Niels-8"

from . import yfinance_source
from .sec_rss_source import SECRSSFeed
from .sec_xbrl_source import SECXBRLApi
from .sec_source_manager import SECSourceManager

__all__ = [
    "yfinance_source",
    "SECRSSFeed",
    "SECXBRLApi",
    "SECSourceManager"
] 