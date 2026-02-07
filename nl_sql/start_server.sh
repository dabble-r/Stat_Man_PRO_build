#!/bin/bash
# Start the FastAPI server for the NL-to-SQL MCP service

cd "$(dirname "$0")"

echo "============================================================"
echo "Starting NL-to-SQL MCP Server"
echo "============================================================"
echo "Server will run at: http://localhost:8000"
echo "API endpoint: http://localhost:8000/nl_to_sql"
echo "API docs: http://localhost:8000/docs"
echo "============================================================"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Check if uvicorn is installed
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "ERROR: uvicorn not found. Installing..."
    pip install uvicorn fastapi
fi

# Start the server
python3 -m uvicorn api_call:app --host 0.0.0.0 --port 8000 --reload
