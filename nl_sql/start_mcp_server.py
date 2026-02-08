"""
Startup script for MCP server (Port 8001).

This script starts the MCP server for database operations.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ.setdefault("STATMANG_ENABLE_RELOAD", "false")

if __name__ == "__main__":
    import uvicorn
    
    # Import app after path is set
    from mcp_server import app
    
    print("Starting MCP server on port 8001...")
    print("Health check available at: http://localhost:8001/health")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info",
            reload=False  # Disable reload for subprocess execution
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
