#!/bin/bash
# Script to start the SQLite Explorer MCP server.

echo "Starting SQLite Explorer MCP Server..."

# Ensure we are in the correct directory
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR"

# Check if a virtual environment exists and activate it
if [ -d "myenv" ]; then
    echo "Activating virtual environment: myenv"
    source myenv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment: venv"
    source venv/bin/activate
else
    echo "No virtual environment found. Using system Python."
    echo "Consider creating and activating a virtual environment for dependency management."
fi

# Check if uvicorn is installed
if ! python -c "import uvicorn" &> /dev/null; then
    echo "Uvicorn not found. Installing..."
    pip install uvicorn fastapi
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install uvicorn and fastapi. Please install manually: pip install uvicorn fastapi"
        exit 1
    fi
fi

# Run the MCP server
python start_mcp_server.py

if [ $? -ne 0 ]; then
    echo "Error: MCP server failed to start."
    exit 1
fi
