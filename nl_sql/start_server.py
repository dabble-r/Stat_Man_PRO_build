#!/usr/bin/env python3
"""
Start the FastAPI server for the NL-to-SQL MCP service.

Usage:
    python start_server.py
    
Or with uvicorn directly:
    uvicorn api_call:app --host 0.0.0.0 --port 8000 --reload
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

# Verify api_call can be imported (but don't import app object)
try:
    import api_call
except ImportError as e:
    print(f"ERROR: Failed to import api_call: {e}")
    print("Make sure you're running from the demo directory and all dependencies are installed.")
    sys.exit(1)

if __name__ == "__main__":
    import os
    
    print("=" * 60)
    print("Starting NL-to-SQL MCP Server")
    print("=" * 60)
    print(f"Server will run at: http://localhost:8000")
    print(f"API endpoint: http://localhost:8000/nl_to_sql")
    print(f"API docs: http://localhost:8000/docs")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")

    try:
        # Check if running from GUI (QProcess) - disable reload in that case
        # Reload uses multiprocessing which can cause issues when run as subprocess
        enable_reload = os.environ.get("STATMANG_ENABLE_RELOAD", "false").lower() == "true"
        
        if enable_reload:
            # Use import string format for reload to work properly
            # Note: reload=True uses multiprocessing, which requires __name__ == '__main__' guard
            uvicorn.run(
                "api_call:app",  # Import string format required for reload
                host="0.0.0.0",
                port=8000,
                reload=True,  # Auto-reload on code changes
                log_level="info"
            )
        else:
            # Import app directly when reload is disabled (safer for subprocess execution)
            from api_call import app
            uvicorn.run(
                app,  # Can use app object when reload is disabled
                host="0.0.0.0",
                port=8000,
                reload=False,  # Disabled for subprocess execution
                log_level="info"
            )
        
    except ImportError as e:
        print(f"ERROR: Missing required package: {e}")
        print("\nInstall required packages with:")
        print("  pip install fastapi uvicorn openai")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: Failed to start server: {e}")
        sys.exit(1)
