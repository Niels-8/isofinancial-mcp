"""
IsoFinancial-MCP - Open-source MCP server for financial market data

A Model Context Protocol (MCP) server providing comprehensive financial market data
endpoints for short squeeze detection and analysis using free APIs.
"""

__version__ = "0.2.0"
__author__ = "Niels-8"
__email__ = "niels-8@github.com"

from .server import server

__all__ = ["server"] 