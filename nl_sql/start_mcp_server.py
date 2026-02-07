#!/usr/bin/env python3
"""
Start the SQLite Explorer MCP server.

Usage:
    python start_mcp_server.py
"""

import sys
from pathlib import Path

# Add demo directory to path
demo_dir = Path(__file__).parent
if str(demo_dir) not in sys.path:
    sys.path.insert(0, str(demo_dir))

try:
    import uvicorn
except ImportError:
    print("ERROR: uvicorn is not installed.")
    print("Install with: pip install uvicorn")
    sys.exit(1)

try:
    from mcp_server import app
except ImportError as e:
    print(f"ERROR: Failed to import mcp_server: {e}")
    print("Make sure you're running from the demo directory and all dependencies are installed.")
    sys.exit(1)

if __name__ == "__main__":
    import os
    
    print("=" * 60)
    print("Starting SQLite Explorer MCP Server")
    print("=" * 60)
    print(f"Server will run at: http://localhost:8001")
    print(f"MCP endpoint: http://localhost:8001/mcp")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")

    try:
        # Check if running from GUI (QProcess) - disable reload in that case
        enable_reload = os.environ.get("STATMANG_ENABLE_RELOAD", "false").lower() == "true"
        
        if enable_reload:
            # Use import string format for reload to work properly
            uvicorn.run(
                "mcp_server:app",  # Import string format required for reload
                host="0.0.0.0",
                port=8001,
                reload=True,
                log_level="info"
            )
        else:
            # Import app directly when reload is disabled (safer for subprocess execution)
            uvicorn.run(
                app,  # Can use app object when reload is disabled
                host="0.0.0.0",
                port=8001,
                reload=False,
                log_level="info"
            )
        
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
