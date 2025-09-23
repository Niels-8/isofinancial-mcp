#!/usr/bin/env python3
"""
Nouveau point d'entrée pour Finance MCP Server avec support uvx
"""

import sys
import asyncio
import argparse
import logging

def main():
    """Point d'entrée principal avec support stdio et HTTP"""
    parser = argparse.ArgumentParser(description='Finance MCP Server')
    parser.add_argument('--mode', choices=['stdio', 'http'], default='stdio',
                       help='Mode de fonctionnement (stdio pour MCP, http pour serveur web)')
    parser.add_argument('--host', default='0.0.0.0', help='Host pour mode HTTP')
    parser.add_argument('--port', type=int, default=8000, help='Port pour mode HTTP')
    
    args = parser.parse_args()
    
    if args.mode == 'stdio':
        # Mode stdio pour MCP (uvx)
        try:
            from iso_financial_mcp import server
            asyncio.run(server.run_stdio_async(show_banner=False))
        except ImportError as e:
            logging.error(f'Error importing FastMCP: {e}')
            logging.error('Make sure fastmcp is installed: pip install fastmcp')
            sys.exit(1)
    else:
        # Mode HTTP pour serveur web
        try:
            import uvicorn
            from iso_financial_mcp import server
            uvicorn.run(server, host=args.host, port=args.port)
        except ImportError as e:
            logging.error(f'Error importing uvicorn: {e}')
            sys.exit(1)

if __name__ == '__main__':
    main()
