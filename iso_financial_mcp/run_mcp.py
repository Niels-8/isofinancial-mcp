#!/usr/bin/env python3
"""
Point d'entrée pour uvx - Finance MCP Server
Lance le serveur en mode stdio pour intégration MCP
"""

from server import server
import sys

def main():
    """Main entry point for running the MCP server via stdio."""
    try:
        # The .run() method on a ToolServer starts it in stdio mode by default.
        server.run()
    except KeyboardInterrupt:
        # Server stopped by user
        pass
    except Exception as e:
        sys.stderr.write(f"Error running IsoFinancial-MCP Server: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main() 