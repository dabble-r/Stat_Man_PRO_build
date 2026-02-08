"""
Startup script for FastAPI server (Port 8000).

This script starts the FastAPI server for NL-to-SQL conversion.
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
    from api_call import app
    
    print("Starting FastAPI server on port 8000...")
    print("API docs available at: http://localhost:8000/docs")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False  # Disable reload for subprocess execution
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
