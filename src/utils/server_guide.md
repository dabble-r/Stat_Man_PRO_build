# MCP Server Implementation Guide

## Overview

This guide outlines the implementation plan for **TWO servers** that work together to provide natural language to SQL query conversion with streaming responses:

1. **FastAPI Server (Port 8000)**: Handles NL-to-SQL conversion using OpenAI
   - Endpoint: `/mcp/ask` or `/nl_to_sql`
   - Requires OpenAI API key
   - Communicates with MCP server for database schema
   - Returns streaming SQL query responses

2. **MCP Server (Port 8001)**: Handles database operations
   - Endpoint: `/health` (health check)
   - Does NOT require API key
   - Provides database schema information
   - Executes SQL queries against SQLite database

**Both servers must be running** for the NL-to-SQL functionality to work properly.

## Code Review

### Provided Code Snippet Analysis

The provided code implements a streamlined MCP server with the following features:

1. **FastAPI Server** (`/mcp/ask` endpoint)
   - Accepts natural language questions
   - Streams responses back to client
   - Integrates OpenAI for SQL generation
   - Validates SQL using sqlglot
   - Executes queries against SQLite database

2. **Key Components:**
   - Schema extraction from SQLite database
   - OpenAI streaming API integration
   - SQL validation (SELECT only, LIMIT required, blocks dangerous operations)
   - SQLite query execution
   - Streaming response format

3. **Security Features:**
   - Only SELECT queries allowed
   - Blocks INSERT, UPDATE, DELETE, DROP, ALTER
   - Requires LIMIT clause
   - Validates SQL syntax before execution

### Issues Identified

1. **Hardcoded Database Path**: `DB_PATH = "League.db"` should use project's path resolver
2. **Hardcoded OpenAI Client**: No API key configuration mechanism
3. **Model Name**: Uses `"gpt-4.1-nano-2025-04-14"` which may not exist
4. **Error Handling**: Limited error handling in streaming response
5. **No Configuration**: Missing environment variable support
6. **Dependencies**: `sqlite3` and `asyncio` are built-in, but `sqlglot` needs to be added to requirements

## Implementation Plan

### ⚠️ CRITICAL: Directory Structure Requirement

**IMPORTANT**: The `NLServerManager` in `src/utils/nl_sql_server.py` expects server files in a **`nl_sql/` directory at the project root**, NOT in `src/servers/`. 

**Required Directory Structure:**
```
project_root/
├── nl_sql/                      # ⚠️ MUST EXIST at project root
│   ├── __init__.py              # Empty file to make it a Python package
│   ├── api_call.py              # FastAPI server (port 8000)
│   ├── mcp_server.py            # MCP server (port 8001)
│   ├── start_server.py          # FastAPI startup script
│   └── start_mcp_server.py      # MCP startup script
├── src/
│   └── utils/
│       └── nl_sql_server.py     # Server manager (expects nl_sql/ at root)
└── tests/
    └── server_test.py           # Test script (expects nl_sql/ at root)
```

**Error Fix**: If you see `FileNotFoundError: NL-SQL directory not found`, you must:
1. Create the `nl_sql/` directory at the project root
2. Create the required server files (see Phase 1 below)
3. Ensure all files are properly implemented before running tests

### Phase 1: Project Structure Setup

1. **Create Server Directory Structure at Project Root**
   ```bash
   # From project root
   mkdir -p nl_sql
   touch nl_sql/__init__.py
   ```
   
   **Required Files in `nl_sql/` directory:**
   ```
   nl_sql/
   ├── __init__.py              # Empty file (makes it a Python package)
   ├── api_call.py              # FastAPI server implementation (port 8000)
   ├── mcp_server.py            # MCP server implementation (port 8001)
   ├── start_server.py          # FastAPI server startup script
   └── start_mcp_server.py      # MCP server startup script
   ```
   
   **Note**: These files must be created before `NLServerManager` or `server_test.py` can work. See detailed implementation in Phase 3 below.

2. **Update Requirements**
   - Add `sqlglot>=23.0.0` to `requirements.txt`
   - Ensure `fastapi>=0.104.0`, `uvicorn>=0.24.0` are present
   - Ensure `openai>=1.0.0` is present

### Phase 2: Configuration Management

**⚠️ Note**: For the actual implementation in `nl_sql/`, API key is passed via HTTP request headers (`Authorization: Bearer <key>`), NOT via a separate config module. The examples below show a conceptual approach, but the actual servers in `nl_sql/` should accept the API key from request headers.

**Conceptual Configuration (for reference):**
- API key management: Passed via HTTP headers in requests
- Database path resolution: Use `from src.utils.path_resolver import get_database_path`
- Model configuration: Default to `gpt-4o-mini` or `gpt-3.5-turbo`
- Port configuration: FastAPI on 8000, MCP on 8001

**Configuration Options:**
```python
- OPENAI_API_KEY: Required, from user input, environment variable, or config file
- DB_PATH: Optional, defaults to get_database_path()
- MODEL_NAME: Optional, defaults to "gpt-4o-mini"
- MCP_PORT: Optional, defaults to 8001
- TEMPERATURE: Optional, defaults to 0
```

**API Key Input Methods (Priority Order):**

1. **GUI Dialog Input (Primary Method)**
   - Prompt user with `QInputDialog.getText()` when API key is needed
   - Use password mode (`QLineEdit.EchoMode.Password`) for security
   - Validate API key format before accepting
   - Store in memory for session (optional: save to secure config file)

2. **Environment Variable**
   - Check `OPENAI_API_KEY` environment variable
   - Useful for automated deployments
   - Overridden by user input if provided

3. **Configuration File (Optional)**
   - Store in `data/config/api_keys.json` or similar
   - Encrypt sensitive data if storing locally
   - Only use if user explicitly opts in

**API Key Input Implementation:**
```python
from PySide6.QtWidgets import QInputDialog, QLineEdit
from PySide6.QtCore import QObject, Signal

class APIKeyManager(QObject):
    """Manages OpenAI API key input and storage."""
    
    api_key_entered = Signal(str)  # Emitted when API key is provided
    
    def get_api_key(self, parent=None) -> Optional[str]:
        """
        Prompt user for OpenAI API key via GUI dialog.
        
        Returns:
            str: API key if provided, None if cancelled
        """
        # Check environment variable first
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # Prompt user via GUI dialog
        api_key, ok = QInputDialog.getText(
            parent,
            "OpenAI API Key Required",
            "Enter your OpenAI API key:",
            echo=QLineEdit.EchoMode.Password,  # Hide input for security
            text=""
        )
        
        if ok and api_key:
            api_key = api_key.strip()
            # Validate API key format (starts with 'sk-')
            if self._validate_api_key(api_key):
                self.api_key_entered.emit(api_key)
                return api_key
            else:
                # Show error and retry
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    parent,
                    "Invalid API Key",
                    "API key must start with 'sk-'. Please try again."
                )
                return self.get_api_key(parent)  # Retry
        
        return None  # User cancelled
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key format."""
        return api_key.startswith("sk-") and len(api_key) > 20
```

### Phase 3: Core Server Implementation

**⚠️ IMPORTANT**: All server files must be created in the `nl_sql/` directory at the project root, NOT in `src/servers/`.

**Required Files to Create:**

1. **`nl_sql/api_call.py`** - FastAPI server (port 8000) for NL-to-SQL conversion
2. **`nl_sql/mcp_server.py`** - MCP server (port 8001) for database operations
3. **`nl_sql/start_server.py`** - FastAPI server startup script
4. **`nl_sql/start_mcp_server.py`** - MCP server startup script
5. **`nl_sql/__init__.py`** - Empty file to make it a Python package

**File: `nl_sql/api_call.py`** (FastAPI Server - Port 8000)

**Refactoring Changes:**
1. **Database Path**: Use `from src.utils.path_resolver import get_database_path`
   ```python
   DB_PATH = get_database_path()
   ```

2. **API Key Management**: 
   - **Primary Method**: Prompt user via GUI dialog when API key is missing
   - Accept API key as parameter or from environment variable
   - Initialize OpenAI client with API key
   - Handle missing API key gracefully with user-friendly prompts
   - Validate API key format before use
   - Support API key update during runtime

3. **Model Configuration**:
   - Use configurable model name (default to `gpt-4o-mini`)
   - Support model selection via configuration

4. **Enhanced Error Handling**:
   - Better error messages in streaming response
   - Handle connection errors gracefully
   - Validate database exists before operations

5. **Improved Streaming**:
   - Add proper error boundaries
   - Include status indicators in stream
   - Better formatting of results

**Enhanced Implementation:**
```python
import sqlite3
import asyncio
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
import sqlglot
from sqlglot import expressions as exp
from src.utils.path_resolver import get_database_path
# Note: API key is passed via HTTP headers, not via config module
# from src.utils.path_resolver import get_database_path

app = FastAPI()

# Use path resolver for database
from src.utils.path_resolver import get_database_path
DB_PATH = get_database_path()

def get_openai_client(api_key: str) -> AsyncOpenAI:
    """Get OpenAI client with API key from request headers."""
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is required. Please provide your API key in Authorization header."
        )
    
    return AsyncOpenAI(api_key=api_key)

# ... rest of implementation with enhanced error handling
```

**File: `nl_sql/mcp_server.py`** (MCP Server - Port 8001)

- Extract database schema with proper error handling
- Format schema for LLM consumption
- Cache schema if database doesn't change frequently
- Support for multiple tables

**File: `nl_sql/start_server.py`** (FastAPI Startup Script)
- Starts FastAPI server on port 8000
- Sets up environment variables
- Handles graceful shutdown

**File: `nl_sql/start_mcp_server.py`** (MCP Server Startup Script)
- Starts MCP server on port 8001
- Sets up environment variables
- Handles graceful shutdown

### Phase 4: Schema Extraction Module

**Note**: Schema extraction can be implemented directly in `api_call.py` or `mcp_server.py`, or as a separate utility module if needed.
   - Support command-line arguments for configuration
   - **Prompt for API key on startup if not provided**
   - Handle graceful shutdown
   - Example implementation:
   ```python
   # src/servers/start_mcp_server.py
   import sys
   from PySide6.QtWidgets import QApplication
   from src.servers.mcp_server import app
   from src.servers.config import APIKeyManager
   import uvicorn
   
   if __name__ == "__main__":
       # Initialize Qt application for GUI dialogs
       qt_app = QApplication(sys.argv)
       
       # Prompt for API key if not in environment
       api_key_manager = APIKeyManager()
       api_key = api_key_manager.get_api_key()
       
       if not api_key:
           print("API key is required. Exiting.")
           sys.exit(1)
       
       # Start FastAPI server
       uvicorn.run(app, host="0.0.0.0", port=8001)
   ```

2. **Integration with Existing Code**
   - If `nl_sql_server.py` is still used, integrate this as the MCP server
   - Update server manager to use new implementation
   - **Add API key prompt when starting servers from GUI**
   - Maintain backward compatibility if possible
   - Example integration:
   ```python
   # In nl_sql_server.py or similar
   def start_mcp_server(self):
       # Check for API key first
       from src.servers.config import APIKeyManager
       api_key_manager = APIKeyManager()
       api_key = api_key_manager.get_api_key(parent=self.parent_widget)
       
       if not api_key:
           self.mcp_failed.emit("API key is required to start MCP server")
           return
       
       # Proceed with server startup...
   ```

### Phase 6: Testing & Validation

1. **Unit Tests**
   - Test SQL validation logic
   - Test schema extraction
   - Test error handling

2. **Integration Tests**
   - Test full request/response cycle
   - Test streaming functionality
   - Test with actual database

3. **Security Tests**
   - Verify dangerous SQL is blocked
   - Test LIMIT requirement enforcement
   - Test SELECT-only enforcement

## Implementation Details

### SQL Validation Rules

The server enforces:
1. **SELECT Only**: Only SELECT queries are allowed
2. **LIMIT Required**: All queries must include a LIMIT clause
3. **Blocked Operations**: INSERT, UPDATE, DELETE, DROP, ALTER are blocked
4. **Syntax Validation**: SQL must be valid SQLite syntax

### Streaming Response Format

The server streams responses in the following format:
```
<SQL tokens streamed from OpenAI>
\n\n---\n\n
RESULTS:\n
<row 1>\n
<row 2>\n
...
```

If errors occur:
```
<SQL tokens>
\n\n---\n\n
SQL ERROR: <error message>
```

### API Endpoint

**POST `/mcp/ask`** (FastAPI Server, Port 8000)

**Important**: This endpoint is on the **FastAPI server (port 8000)**, not the MCP server (port 8001). The FastAPI server handles NL-to-SQL conversion and communicates with the MCP server internally for database schema.

**Request Body:**
```json
{
  "question": "Show me all players with batting average above 0.300"
}
```

**Optional Request Body (with API key):**
```json
{
  "question": "Show me all players with batting average above 0.300",
  "api_key": "sk-..."  // Optional: can provide API key per request
}
```

**Response:**
- Content-Type: `text/plain`
- Streaming response
- Returns SQL query generation stream, followed by execution results

**Error Responses:**
- `400 Bad Request`: Missing API key or invalid request
- `401 Unauthorized`: Invalid API key
- `500 Internal Server Error`: Server-side errors

**API Key Handling:**
- If API key provided in request, use it for that request only
- If no API key in request, use globally configured API key
- If no API key available, return 400 error with message prompting user to provide API key

## Security Considerations

1. **SQL Injection Prevention**
   - All SQL is generated by LLM, not from user input directly
   - SQL validation ensures only SELECT queries
   - sqlglot parsing validates syntax

2. **Database Protection**
   - Read-only operations (SELECT only)
   - LIMIT clause prevents large result sets
   - No data modification allowed

3. **API Key Security**
   - **User Input Security**:
     - Use password mode in input dialogs (hide characters)
     - Validate API key format before accepting
     - Never display API key in logs or error messages
     - Clear API key from memory when no longer needed
   - **Storage Security**:
     - Prefer in-memory storage (session-only)
     - If persisting, use encrypted storage
     - Environment variables are secure for automated deployments
     - Never commit API keys to version control
   - **Validation**:
     - Validate API key format (must start with 'sk-')
     - Test API key validity before processing requests
     - Handle invalid API keys gracefully with user feedback

## Error Handling Strategy

1. **Database Errors**
   - Check database exists before operations
   - Handle connection errors gracefully
   - Return clear error messages

2. **OpenAI API Errors**
   - **API Key Errors**:
     - Detect invalid API key (401 Unauthorized)
     - Prompt user to re-enter API key if invalid
     - Clear cached API key on authentication failure
     - Provide clear error messages: "Invalid API key. Please check and try again."
   - **Rate Limiting**:
     - Handle 429 Too Many Requests
     - Implement exponential backoff
     - Inform user of rate limit status
   - **Model Availability**:
     - Handle model not found errors
     - Fallback to default model if specified model unavailable
     - Clear error messages for model issues

3. **SQL Validation Errors**
   - Return specific validation error messages
   - Suggest fixes when possible
   - Log errors for debugging

## Deployment Considerations

1. **Development Mode**
   - Use `uvicorn` with `--reload` flag
   - Enable debug logging
   - Use development database

2. **Production Mode**
   - Use `uvicorn` with proper workers
   - Disable debug mode
   - Use production database path
   - Set proper timeout values
   - Enable logging to file

3. **Standalone Execution**
   ```bash
   python -m src.servers.start_mcp_server
   ```

4. **With Uvicorn**
   ```bash
   uvicorn src.servers.mcp_server:app --host 0.0.0.0 --port 8001
   ```

## Dependencies

### Required
- `fastapi>=0.104.0` - Web framework
- `uvicorn>=0.24.0` - ASGI server
- `openai>=1.0.0` - OpenAI API client
- `sqlglot>=23.0.0` - SQL parsing and validation
- `pydantic>=2.0.0` - Data validation

### Built-in (No Installation Needed)
- `sqlite3` - SQLite database
- `asyncio` - Async/await support

## Next Steps

1. **Create Server Directory**: Set up `nl_sql/` directory at project root (see Phase 1)
2. **Implement Configuration Module**: 
   - Create `config.py` with proper path resolution
   - **Implement `APIKeyManager` class with GUI dialog support**
   - Add API key validation and storage mechanisms
3. **Refactor MCP Server**: 
   - Update provided code with project-specific integrations
   - **Add API key prompt on startup if missing**
   - Integrate `APIKeyManager` for user input
4. **Create Startup Script**: 
   - Add `start_mcp_server.py` for easy execution
   - **Include Qt application initialization for GUI dialogs**
   - Handle API key input before server starts
5. **Update Server Manager**: 
   - Integrate with existing `nl_sql_server.py` if needed
   - **Add API key prompt when starting servers from GUI**
6. **Add Tests**: 
   - Create unit and integration tests
   - **Test API key input and validation**
   - Test error handling for invalid API keys
7. **Documentation**: 
   - Add API documentation and usage examples
   - **Document API key input methods and security practices**

## Example Usage

### Starting the Server

**With GUI API Key Prompt:**
```python
# Using Python module (will prompt for API key via GUI)
python -m src.servers.start_mcp_server
```

**With Environment Variable:**
```bash
# Set API key in environment
export OPENAI_API_KEY="sk-your-key-here"

# Start server
uvicorn src.servers.mcp_server:app --host 0.0.0.0 --port 8001
```

**With Command Line API Key:**
```python
# In start_mcp_server.py, can accept --api-key argument
python -m src.servers.start_mcp_server --api-key "sk-..."
```

### Making a Request

**Basic Request (uses server's configured API key):**
```python
import requests

response = requests.post(
    "http://localhost:8000/mcp/ask",  # FastAPI server on port 8000
    json={"question": "Show me all teams with more than 10 wins"},
    stream=True
)

for chunk in response.iter_content(chunk_size=1024):
    print(chunk.decode(), end='')
```

**Request with API Key (overrides server's API key for this request):**
```python
import requests

response = requests.post(
    "http://localhost:8000/mcp/ask",  # FastAPI server on port 8000
    json={
        "question": "Show me all teams with more than 10 wins",
        "api_key": "sk-your-key-here"  # Optional: per-request API key
    },
    stream=True
)

for chunk in response.iter_content(chunk_size=1024):
    print(chunk.decode(), end='')
```

### GUI Integration Example

**Prompting for API Key in GUI Application:**
```python
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit
from src.servers.config import APIKeyManager

# In your GUI application
app = QApplication([])

# Create API key manager
api_key_manager = APIKeyManager()

# Prompt user for API key (will show password dialog)
api_key = api_key_manager.get_api_key(parent=main_window)

if api_key:
    print("API key provided, starting server...")
    # Start server with API key
else:
    print("User cancelled API key entry")
```

## Critical Errors and Corrections

**⚠️ IMPORTANT: Review the following errors before implementation**

### 1. FastAPI Cannot Use GUI Dialogs (CRITICAL)
**Location**: Lines 212-229

**Error**: The `get_openai_client()` function attempts to call `api_key_manager.get_api_key()` which shows a GUI dialog. FastAPI endpoints run as web servers with no GUI/QApplication available.

**Correction**: 
- API key must be provided via HTTP request headers (`Authorization: Bearer <key>`) or request body
- GUI dialogs can only be used BEFORE the server starts (in startup script or GUI application)
- FastAPI endpoints should accept API key from request, not prompt for it

**Corrected Implementation**:
```python
from fastapi import Header, HTTPException
from typing import Optional

@app.post("/mcp/ask")
async def ask(
    query: Query,
    authorization: Optional[str] = Header(None)
):
    # Get API key from Authorization header or request body
    api_key = None
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]
    elif hasattr(query, 'api_key') and query.api_key:
        api_key = query.api_key
    else:
        # Check environment variable as fallback
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API key required. Provide via Authorization header or request body."
        )
    
    # Create client with API key for this request
    client = AsyncOpenAI(api_key=api_key)
    # ... rest of implementation
```

### 2. Missing Imports in Code Examples
**Location**: Lines 100-152

**Error**: Code examples are missing required imports.

**Correction**: Add imports at the top:
```python
import os
from typing import Optional
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
from PySide6.QtCore import QObject, Signal
```

### 3. API Key Priority Order Inconsistency
**Location**: Lines 65-68 vs 117-120

**Error**: Documentation says GUI is "primary method" but code checks environment variable first.

**Correction**: Update documentation to reflect actual priority:
1. Environment variable `OPENAI_API_KEY` (for automated/server deployments)
2. GUI dialog input (for interactive GUI applications)
3. Configuration file (optional)

### 4. Database Path Logic Error
**Location**: Line 210

**Error**: `config.DB_PATH or get_database_path()` will use empty string if `config.DB_PATH` is `""`.

**Correction**:
```python
DB_PATH = config.DB_PATH if config.DB_PATH else get_database_path()
# Or more explicit:
DB_PATH = config.DB_PATH if (config.DB_PATH and config.DB_PATH.strip()) else get_database_path()
```

### 5. Thread Safety Issue
**Location**: Lines 206-207

**Error**: Global `client` variable is not thread-safe for concurrent requests.

**Correction**: Create client per request or use thread-safe storage:
```python
# Option 1: Per-request client (recommended)
def get_openai_client(api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key)

# Option 2: Thread-safe global with locking
import threading
_client_lock = threading.Lock()
_client: Optional[AsyncOpenAI] = None

def get_openai_client(api_key: str) -> AsyncOpenAI:
    global _client
    with _client_lock:
        if _client is None:
            _client = AsyncOpenAI(api_key=api_key)
        return _client
```

### 6. Missing UI Workflow Description
**Error**: The guide doesn't document the complete UI workflow with two-panel layout.

**Correction**: See "UI Workflow Implementation" section below.

### 7. API Key Validation Too Restrictive
**Location**: Line 151

**Error**: Validation only checks `startswith("sk-")` which may reject valid keys.

**Correction**: Use more flexible validation or test against OpenAI API:
```python
def _validate_api_key(self, api_key: str) -> bool:
    """Validate API key format."""
    if not api_key or len(api_key) < 20:
        return False
    # Basic format check - OpenAI keys typically start with sk-
    # But allow other formats for organization keys
    return api_key.startswith("sk-") or len(api_key) > 40
```

### 8. Error Handling in Streaming Response
**Location**: Lines 325-340

**Error**: Error format unclear if error occurs before any tokens.

**Correction**: Define clear error format:
```python
async def stream():
    try:
        # ... SQL generation
    except Exception as e:
        # Clear error format even if no tokens generated
        yield f"ERROR: {str(e)}\n"
        return
```

### 9. HTTPException in Streaming Context
**Location**: Lines 222-226

**Error**: `get_openai_client()` raises `HTTPException` if no API key, but this is called from streaming endpoint. HTTPException might not work correctly in streaming response.

**Correction**: Handle error in stream itself, return error message in stream format:
```python
async def stream():
    api_key = get_api_key_from_request()
    if not api_key:
        yield "ERROR: API key required. Provide via Authorization header or request body.\n"
        return
    # ... rest of streaming logic
```

### 10. Server Startup Script Conflict
**Location**: Lines 251-273 (start_mcp_server.py)

**Error**: Script initializes `QApplication` for GUI dialogs, but if server is started via `uvicorn` command line, no QApplication exists. Creates inconsistent behavior between startup methods.

**Correction**: Document that GUI dialogs only work when started via Python module. Command-line uvicorn requires environment variable or config file.

## Additional Issues and Concerns

### Missing Implementation Details

#### 11. No API Key Testing Mechanism
**Location**: Throughout document

**Issue**: Documentation says "Test API key validity before processing requests" but no implementation shown for how to test API key. No example of calling OpenAI API to validate key.

**Fix**: Add API key validation implementation example:
```python
async def validate_api_key(api_key: str) -> bool:
    """Validate API key by making a test request to OpenAI."""
    try:
        client = AsyncOpenAI(api_key=api_key)
        # Make a minimal test request
        response = await client.models.list()
        return True
    except Exception:
        return False
```

#### 12. Schema Caching Not Implemented
**Location**: Line 240

**Issue**: Documentation mentions "Cache schema if database doesn't change frequently" but no implementation details or cache invalidation strategy.

**Fix**: Add schema caching implementation details:
```python
from functools import lru_cache
from pathlib import Path
import hashlib

_schema_cache = {}
_db_hash_cache = {}

def get_schema_cached(db_path: Path) -> str:
    """Get database schema with caching."""
    # Calculate database file hash
    db_hash = _calculate_db_hash(db_path)
    
    # Check if schema is cached and database hasn't changed
    if db_path in _schema_cache and _db_hash_cache.get(db_path) == db_hash:
        return _schema_cache[db_path]
    
    # Extract and cache schema
    schema = get_schema(db_path)
    _schema_cache[db_path] = schema
    _db_hash_cache[db_path] = db_hash
    
    return schema

def _calculate_db_hash(db_path: Path) -> str:
    """Calculate hash of database file for cache invalidation."""
    with open(db_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()
```

#### 13. Missing Error Recovery
**Location**: Error handling sections

**Issue**: No description of how to recover from errors. No retry logic for transient failures. No user feedback mechanism for long-running operations.

**Fix**: Add error recovery and retry strategies:
```python
import asyncio
from typing import Callable, Any

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Any:
    """Retry function with exponential backoff."""
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= backoff_factor
    
    raise last_exception
```

### Security Concerns

#### 14. API Key in Request Body
**Location**: Lines 353-359

**Issue**: Allows API key in request body (optional). API keys in request bodies are less secure than headers. Should use Authorization header instead.

**Fix**: Recommend Authorization header for API key in requests:
```python
# Preferred: Use Authorization header
headers = {"Authorization": f"Bearer {api_key}"}

# Fallback: Request body (less secure, for compatibility only)
body = {"question": query, "api_key": api_key}
```

#### 15. No Rate Limiting
**Location**: Throughout document

**Issue**: No mention of rate limiting implementation. Could allow abuse of OpenAI API. No cost controls.

**Fix**: Add rate limiting and cost control recommendations:
```python
from collections import deque
import time

class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
    
    def can_make_request(self) -> bool:
        """Check if request can be made within rate limit."""
        now = time.time()
        # Remove old calls outside time window
        while self.calls and self.calls[0] < now - self.time_window:
            self.calls.popleft()
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False

# Usage: Limit to 10 calls per minute
rate_limiter = RateLimiter(max_calls=10, time_window=60.0)

@app.post("/mcp/ask")
async def ask(query: Query):
    if not rate_limiter.can_make_request():
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # ... process request
```

### Documentation Issues

#### 16. Incomplete Code Examples
**Location**: Multiple locations

**Issue**: Code examples are fragments, not complete implementations. Missing error handling in examples. No complete working example.

**Fix**: Add complete, runnable code examples in separate sections with full context.

#### 17. Missing Dependencies Notes
**Location**: Lines 455-466

**Issue**: Lists `sqlite3` and `asyncio` as "Built-in" but `sqlite3` might not be available in all Python distributions. Should note platform-specific considerations.

**Fix**: Add platform-specific notes:
- `sqlite3`: Built-in for Python 2.5+, but may require `pysqlite3` on some systems
- `asyncio`: Built-in for Python 3.4+
- Platform-specific: Some embedded Python distributions may exclude these modules

## Server Startup Logic - Critical Corrections

**⚠️ IMPORTANT: The following corrections address critical server startup workflow issues**

### Problem: Only MCP Server Mentioned in Workflow

**Issue**: The original workflow and GUI implementation only mentioned starting "MCP server", but the system requires **TWO servers**:
- **FastAPI Server (Port 8000)**: Handles NL-to-SQL conversion, requires API key
- **MCP Server (Port 8001)**: Handles database operations, does NOT require API key

**Correction**: 
- Updated workflow step 2 to start **BOTH servers** when API key is submitted
- Updated GUI implementation to use `NLServerManager` which manages both servers
- Added health checks for both servers before enabling NL query section

### Problem: Incorrect Server Architecture

**Issue**: The guide was unclear about which server handles what functionality.

**Correction**:
- **FastAPI Server (8000)**: Receives NL queries, calls OpenAI API, returns SQL
- **MCP Server (8001)**: Provides database schema, executes SQL queries
- Both must be running for full functionality

### Problem: Missing Server Manager Integration

**Issue**: GUI implementation showed starting servers directly instead of using `NLServerManager`.

**Correction**: 
- Use `NLServerManager` from `src.utils.nl_sql_server`
- Manager handles both servers, signals, and health checks
- Connect to `all_servers_ready` signal to enable NL query section

### Problem: Health Check Only for One Server

**Issue**: Code examples only checked MCP server health, not FastAPI server.

**Correction**:
- Check FastAPI: `http://localhost:8000/health` (should return 200)
- Check MCP: `http://localhost:8001/health` (should return 200)
- Enable NL query section only when BOTH are ready

### Problem: API Key Usage Unclear

**Issue**: Guide didn't clarify which server needs the API key.

**Correction**:
- FastAPI server: **Requires** API key (for OpenAI integration)
- MCP server: **Does NOT require** API key (database operations only)
- API key is passed to FastAPI server via environment variable or config

### Server Startup Sequence (Corrected)

1. User submits API key
2. Validate API key format
3. **Start FastAPI server (port 8000) with API key**
4. **Start MCP server (port 8001) without API key**
5. Poll health endpoints for both servers
6. If both ready: Enable NL query section
7. If either fails: Show error, allow retry

### Server Shutdown

**Implementation**: Add to dialog close handler:
```python
def closeEvent(self, event):
    """Stop servers when dialog closes."""
    if hasattr(self, 'server_manager'):
        self.server_manager.stop_all_servers()
    super().closeEvent(event)
```

## Comprehensive Recommendations

1. **Separate GUI and Server Concerns**: 
   - GUI API key input should happen BEFORE server starts
   - Server should only accept API key via HTTP headers/body
   - No GUI dialogs from FastAPI endpoints

2. **Add Complete UI Workflow Section**:
   - Document the two-panel layout
   - Step-by-step user flow
   - Widget enablement logic
   - State management
   - *(Note: This has been added in the "UI Workflow Implementation" and "PySide6 GUI Implementation Plan" sections)*

3. **Fix Priority Order**:
   - Make priority order consistent between docs and code
   - Document when each method is appropriate
   - Priority: Environment variable → GUI input → Config file

4. **Add Thread Safety**:
   - Document thread-safety concerns
   - Provide thread-safe implementation patterns
   - Use per-request client creation (recommended)

5. **Complete Error Handling**:
   - Define all error scenarios
   - Provide recovery strategies
   - Add user feedback mechanisms
   - Implement retry logic for transient failures

6. **Security Best Practices**:
   - Use Authorization headers for API keys
   - Implement rate limiting
   - Add cost controls
   - Never log API keys
   - Validate all inputs

7. **Performance Optimization**:
   - Implement schema caching
   - Use connection pooling for database
   - Optimize streaming response handling
   - Monitor resource usage

## UI Workflow Implementation (ALTERNATIVE APPROACH)

**⚠️ NOTE**: This section describes an **alternative two-panel layout approach** where the NL-to-SQL interface is integrated directly into the search dialog. 

**The recommended implementation** is the **"Search Dialog Integration Implementation"** section below, which uses a radio button toggle to show a separate `NLQueryDialog`. This approach provides better separation of concerns and is the currently implemented solution.

**See "Search Dialog Integration Implementation"** for the recommended approach.

### Dialog Layout Structure (Alternative Approach)

The search dialog should implement a **two-panel layout**:

```
┌─────────────────────────────────────────────────────┐
│              Search Dialog                          │
├──────────────────────┬──────────────────────────────┤
│   LEFT PANEL         │   RIGHT PANEL                │
│                      │                              │
│  [API Key Input]     │  [SQL Query Display]        │
│  [Submit API Key]    │  [Formatted SQL]             │
│  (enabled)           │  (disabled initially)        │
│                      │                              │
│  [NL Query Input]    │  [Submit SQL Button]         │
│  [Submit NL Query]   │  (disabled initially)        │
│  (disabled initially)│                              │
└──────────────────────┴──────────────────────────────┘
```

### Workflow Steps (Alternative Approach - Two-Panel Layout in Search Dialog)

**Note**: This workflow describes the alternative two-panel layout approach. For the **recommended radio button toggle implementation**, see "Search Dialog Integration Implementation" section below.

1. **User clicks Search button from main window**
   - Dialog opens with two-panel layout directly in search dialog
   - Left panel: API key input (top) and NL query input (bottom)
   - Right panel: SQL query display area (initially empty/disabled)

2. **API Key Input (Top Left)**
   - User enters API key in input field
   - User clicks "Submit API Key" button
   - Validate API key format
   - If valid:
     - Store API key in memory
     - **Start BOTH FastAPI server (port 8000) and MCP server (port 8001)**
     - FastAPI server requires API key for OpenAI integration
     - MCP server does NOT require API key (database operations only)
     - Wait for both servers to respond to health checks
     - Enable NL query input and submit button **only after BOTH servers are ready**
     - Show success message
   - If invalid:
     - Show error message
     - Keep NL query disabled
   - **Server Startup Sequence**:
     1. Validate API key format
     2. Start FastAPI server (port 8000) with API key
     3. Start MCP server (port 8001) without API key
     4. Poll health endpoints: `/health` (FastAPI) and `/health` (MCP)
     5. If both ready: Enable NL query section
     6. If either fails: Show error, allow retry

3. **Natural Language Query (Bottom Left)**
   - User enters natural language query
   - User clicks "Submit NL Query" button
   - **Send request to FastAPI server** (`http://localhost:8000/mcp/ask` or `/nl_to_sql`)
   - FastAPI server uses API key to call OpenAI for SQL generation
   - Show loading indicator
   - On success:
     - Display formatted SQL query on right panel
     - Enable SQL submit button
   - On error:
     - Show error message
     - Keep SQL submit disabled
   - **Note**: FastAPI server handles NL-to-SQL conversion, MCP server is used internally for schema

4. **SQL Query Display (Right Panel)**
   - Display formatted SQL query (read-only)
   - Show "Submit SQL" button (enabled after NL query success)

5. **SQL Execution**
   - User clicks "Submit SQL" button
   - Execute SQL query against database
   - On success:
     - Open new dialog with results
     - Display results in tree widget with appropriate headers
   - On error:
     - Show error message in dialog

### Implementation Notes

- **Widget Enablement Logic**:
  - API key input: Always enabled
  - NL query input: Enabled only after valid API key submitted
  - SQL submit button: Enabled only after successful NL query
  - Results dialog: Opens only after successful SQL execution

- **State Management**:
  - Track API key validation state
  - Track **both** server startup states (FastAPI and MCP)
  - Track server readiness (both must be ready before enabling NL query)
  - Track NL query processing state
  - Track SQL execution state

- **Error Handling**:
  - Clear error messages for each step
  - Disable dependent widgets on errors
  - Allow retry at each step

## PySide6 GUI Implementation Plan (ALTERNATIVE APPROACH)

**⚠️ NOTE**: This section describes an **alternative custom `NLSearchDialog` class approach** that replaces the existing `SearchDialog`.

**The recommended implementation** is the **"Search Dialog Integration Implementation"** section below, which uses a radio button toggle to show a separate `NLQueryDialog` while keeping the existing `SearchDialog` structure. This approach provides better integration with existing code and is the currently implemented solution.

**See "Search Dialog Integration Implementation"** for the recommended approach.

### Overview (Alternative Approach)

This section details an alternative approach where a custom `NLSearchDialog` class replaces the existing `SearchDialog`.

**Key Integration Points** (Alternative):
- Custom `NLSearchDialog` class with two-panel layout
- Servers start when API key is submitted
- Servers stop when dialog closes
- Results are displayed in a separate results dialog

**See `server_implement_analysis.md`** for detailed analysis and corrections.

### Architecture Overview (Alternative Approach)

#### Dialog Structure

```
SearchDialog (extends BaseDialog)
├── Two-Panel Layout (QHBoxLayout)
│   ├── Left Panel (QVBoxLayout)
│   │   ├── API Key Section
│   │   │   ├── QLabel: "OpenAI API Key"
│   │   │   ├── QLineEdit: API key input (password mode)
│   │   │   └── QPushButton: "Submit API Key"
│   │   └── NL Query Section
│   │       ├── QLabel: "Natural Language Query"
│   │       ├── QTextEdit: Query input (multi-line)
│   │       └── QPushButton: "Submit NL Query"
│   └── Right Panel (QVBoxLayout)
│       ├── QLabel: "Generated SQL Query"
│       ├── QTextEdit: SQL display (read-only, formatted)
│       └── QPushButton: "Execute SQL"
└── Results Dialog (separate QDialog)
    └── QTreeWidget: Query results display
```

### Implementation Phases

#### Phase 1: Dialog Structure and Layout

**File**: `src/ui/dialogs/search_dialog.py`

**Tasks**:
1. Create custom dialog class extending `BaseDialog`
2. Override `_setup_dialog()` to create two-panel layout
3. Create widget containers for left and right panels
4. Set initial dialog size (900x650 recommended)

**Implementation**:
```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QDialog, QTreeWidget
)
from PySide6.QtCore import Qt, QThread, Signal
from typing import Optional
from src.ui.dialogs.base_dialog import BaseDialog

class NLSearchDialog(BaseDialog):
    """Dialog for natural language to SQL query conversion."""
    
    def __init__(self, league, selected, stack, undo, message, parent=None):
        # Create custom template for two-panel layout
        template = {
            'title': 'Natural Language Query',
            'size': (900, 650),
            'layout': 'custom',
            'custom_setup': self._setup_custom_layout
        }
        
        context = {
            'league': league,
            'selected': selected,
            'stack': stack,
            'undo': undo,
            'message': message
        }
        
        super().__init__(template, context, parent=parent)
        
        # State management
        self.api_key: Optional[str] = None
        self.api_key_validated: bool = False
        self.fastapi_server_url: str = "http://localhost:8000"
        self.mcp_server_url: str = "http://localhost:8001"
        self.generated_sql: Optional[str] = None
        
        # Initialize widgets
        self._init_widgets()
        self._setup_widget_states()
    
    def _setup_custom_layout(self):
        """Setup two-panel custom layout."""
        # Main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Left panel
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, stretch=1)
        
        # Set layout
        self.setLayout(main_layout)
```

#### Phase 2: Widget Creation

**Tasks**:
1. Create API key input section
2. Create NL query input section
3. Wire up button handlers
4. Implement widget state management

**Key Methods**:
- `_init_widgets()`: Initialize all dialog widgets
- `_create_api_key_section()`: Create API key input section
- `_create_nl_query_section()`: Create natural language query section
- `_create_right_panel()`: Create SQL display panel
- `_setup_widget_states()`: Set initial widget enablement states

#### Phase 3: API Key Validation and Server Startup

**Tasks**:
1. Implement API key validation
2. **Start BOTH FastAPI server (port 8000) and MCP server (port 8001)**
3. Verify both servers are ready via health checks
4. Update widget states on success/failure
5. Handle server startup errors

**Key Methods**:
- `_handle_api_key_submit()`: Handle API key submission
- `_validate_api_key_format()`: Validate API key format
- `_validate_and_start_servers()`: Validate API key and start BOTH servers (async)
- `_on_all_servers_ready()`: Handle when both servers are ready
- `_check_servers_ready()`: Check health of both servers

**Implementation Notes**:
- Use `NLServerManager` from `src.utils.nl_sql_server` to manage both servers
- FastAPI server (port 8000): Requires API key for OpenAI integration
- MCP server (port 8001): Does NOT require API key (database operations only)
- Use `QThread` or `NLServerManager` signals for async server startup
- Test BOTH server health endpoints to verify readiness:
  - FastAPI: `http://localhost:8000/health` (should return 200)
  - MCP: `http://localhost:8001/health` (should return 200)
- Mask API key in UI after validation
- Enable NL query section only after BOTH servers are ready

**Corrected Implementation**:
```python
from src.utils.nl_sql_server import NLServerManager

def _validate_and_start_servers(self, api_key: str):
    """Start BOTH FastAPI and MCP servers."""
    # Create server manager (if not already created)
    if not hasattr(self, 'server_manager'):
        self.server_manager = NLServerManager(parent=self)
        
        # Connect signals
        self.server_manager.all_servers_ready.connect(self._on_all_servers_ready)
        self.server_manager.fastapi_ready.connect(self._on_fastapi_ready)
        self.server_manager.mcp_ready.connect(self._on_mcp_ready)
        self.server_manager.fastapi_failed.connect(self._on_fastapi_failed)
        self.server_manager.mcp_failed.connect(self._on_mcp_failed)
    
    # Store API key (will be used by FastAPI server via environment or config)
    self.api_key = api_key
    
    # Set API key in environment for FastAPI server
    import os
    os.environ['OPENAI_API_KEY'] = api_key
    
    # Start BOTH servers
    self.server_manager.start_fastapi_server(
        output_callback=self._on_fastapi_output,
        error_callback=self._on_fastapi_error
    )
    self.server_manager.start_mcp_server(
        output_callback=self._on_mcp_output,
        error_callback=self._on_mcp_error
    )

def _on_all_servers_ready(self):
    """Called when both servers are ready."""
    self.api_key_validated = True
    self._show_success("Both servers are ready. You can now submit queries.")
    
    # Enable NL query section
    self.nl_query_input.setEnabled(True)
    self.submit_nl_query_button.setEnabled(True)
    
    # Update API key input (mask it)
    masked_key = self.api_key[:7] + "*" * (len(self.api_key) - 11) + self.api_key[-4:]
    self.api_key_input.setText(masked_key)
    self.api_key_input.setReadOnly(True)

def _on_server_started(self, success: bool, message: str, api_key: str):
    """Handle server startup result - DEPRECATED, use _on_all_servers_ready instead."""
    # This method is replaced by signal handlers above
    pass
```

#### Phase 4: Natural Language Query Processing

**Tasks**:
1. Send NL query to **FastAPI server** (port 8000)
2. Handle streaming response
3. Parse SQL from response
4. Display formatted SQL on right panel
5. Enable SQL execute button

**Key Methods**:
- `_handle_nl_query_submit()`: Handle natural language query submission
- `_send_nl_query()`: Send natural language query to FastAPI server (async)
- `_on_nl_query_complete()`: Handle NL query completion
- `_display_sql_query()`: Display formatted SQL query in right panel
- `_format_sql_query()`: Format SQL query for better readability

**Response Parsing**:
- Parse streaming response format: `<SQL tokens>\n\n---\n\nRESULTS:\n<results>`
- Extract SQL query before the `---` separator
- Handle error messages in response
- Format SQL with proper line breaks

#### Phase 5: SQL Execution and Results Display

**Tasks**:
1. Execute SQL query against database
2. Handle query results
3. Create results dialog
4. Display results in tree widget

**Key Methods**:
- `_execute_sql_query()`: Execute SQL query and display results
- `_run_sql_query()`: Execute SQL query in background thread
- `_on_sql_execution_complete()`: Handle SQL execution completion
- `_show_results_dialog()`: Create and show results dialog with tree widget

**Results Dialog**:
- Separate `QDialog` window
- `QTreeWidget` for tabular results display
- Show SQL query and row count
- Proper column headers and alignment

#### Phase 6: Error Handling and Status Messages

**Tasks**:
1. Implement error message display
2. Implement success message display
3. Handle all error scenarios
4. Provide user feedback

**Key Methods**:
- `_show_error()`: Show error message to user
- `_show_success()`: Show success message to user

**Error Scenarios**:
1. Invalid API Key Format: Show error, allow retry
2. **FastAPI Server Startup Failure**: Show error, reset state, allow retry
3. **MCP Server Startup Failure**: Show error, reset state, allow retry
4. **One Server Ready, Other Failed**: Show partial error, don't enable NL query
5. FastAPI Server Connection Error: Show error, allow retry
6. MCP Server Connection Error: Show error, allow retry
7. Invalid SQL Generation: Show error, clear SQL display
8. SQL Execution Error: Show error, keep SQL displayed

#### Phase 7: Integration with Main Window

**Tasks**:
1. Update main window search button handler
2. Replace existing SearchDialog with NLSearchDialog
3. Handle dialog lifecycle

**Implementation**:
```python
# In main_window.py
def setup_search_ui(self):
    """Open natural language search dialog."""
    if not self.league.teams:
        self.message.show_message("There are no teams in league.", btns_flag=False, timeout_ms=2000)
        return
    
    # Use new NL search dialog
    from src.ui.dialogs.search_dialog import NLSearchDialog
    dialog = NLSearchDialog(
        self.league, 
        self.selected, 
        self.stack, 
        self.undo, 
        self.message, 
        parent=self
    )
    dialog.exec()
```

### File Structure

```
src/ui/dialogs/
├── search_dialog.py          # Main NL search dialog (NEW/REPLACE)
├── base_dialog.py            # Base dialog class (existing)
├── dialog_handlers.py        # Update search handler (if needed)
└── template_configs.py       # Update search template (if needed)

nl_sql/
├── __init__.py              # Empty file (Python package)
├── api_call.py              # FastAPI server (port 8000)
├── mcp_server.py            # MCP server (port 8001)
├── start_server.py          # FastAPI startup script
└── start_mcp_server.py      # MCP startup script
```

### State Management

#### Dialog States

1. **Initial State**:
   - API key input: Enabled
   - NL query input: Disabled
   - SQL display: Disabled
   - Execute SQL button: Disabled

2. **After API Key Validation**:
   - API key input: Read-only (masked)
   - NL query input: Enabled
   - SQL display: Disabled
   - Execute SQL button: Disabled

3. **After NL Query Success**:
   - API key input: Read-only
   - NL query input: Enabled
   - SQL display: Enabled (with query)
   - Execute SQL button: Enabled

4. **Error States**:
   - On API key error: Reset to initial state
   - On NL query error: Keep API key validated, allow retry
   - On SQL error: Keep SQL displayed, allow retry

### Testing Checklist

- [ ] Dialog opens with correct layout
- [ ] API key input accepts and validates format
- [ ] **BOTH FastAPI and MCP servers start successfully with valid API key**
- [ ] FastAPI server health check passes (port 8000)
- [ ] MCP server health check passes (port 8001)
- [ ] NL query section enables only after BOTH servers ready
- [ ] NL query section enables after API key validation
- [ ] NL query sends request to FastAPI server (port 8000)
- [ ] SQL query displays correctly on right panel
- [ ] SQL execute button enables after query generation
- [ ] SQL execution works correctly
- [ ] Results dialog displays correctly
- [ ] Error messages show for all error scenarios
- [ ] Widget states update correctly
- [ ] Thread safety (no GUI updates from background threads)
- [ ] Dialog closes cleanly

### Performance Considerations

1. **Async Operations**: All server communication and SQL execution in background threads
2. **Streaming**: Handle MCP server streaming response efficiently
3. **UI Responsiveness**: Keep UI responsive during long operations
4. **Memory**: Clean up threads and connections properly

### Security Considerations

1. **API Key Storage**: Store in memory only, never log
2. **API Key Display**: Mask in UI after validation
3. **SQL Validation**: Server-side validation (already implemented)
4. **Input Sanitization**: Validate all user inputs

### Future Enhancements

1. **Query History**: Save previous queries
2. **Query Templates**: Pre-defined query templates
3. **Export Results**: Export results to CSV/Excel
4. **Query Editing**: Allow manual SQL editing before execution
5. **Multiple Databases**: Support multiple database selection
6. **Query Optimization**: Show query execution time and optimization suggestions

## Troubleshooting

### Error: "NL-SQL directory not found"

**Symptom**: 
```
FileNotFoundError: NL-SQL directory not found: /path/to/project/nl_sql
Please ensure the nl_sql directory exists in the project root.
```

**Cause**: The `nl_sql/` directory does not exist at the project root, or required files are missing.

**Solution**:
1. **Create the directory structure**:
   ```bash
   # From project root
   mkdir -p nl_sql
   touch nl_sql/__init__.py
   ```

2. **Create required server files**:
   - `nl_sql/api_call.py` - FastAPI server implementation
   - `nl_sql/mcp_server.py` - MCP server implementation
   - `nl_sql/start_server.py` - FastAPI startup script
   - `nl_sql/start_mcp_server.py` - MCP startup script

3. **Verify directory structure**:
   ```bash
   # From project root
   ls -la nl_sql/
   # Should show:
   # __init__.py
   # api_call.py
   # mcp_server.py
   # start_server.py
   # start_mcp_server.py
   ```

4. **Test server startup**:
   ```bash
   # Run test script
   python tests/server_test.py
   ```

### Error: "Module not found" when starting servers

**Symptom**: Server fails to start with import errors.

**Cause**: `PYTHONPATH` not set correctly, or dependencies not installed.

**Solution**:
1. Ensure all dependencies are installed:
   ```bash
   pip install fastapi uvicorn openai sqlglot pydantic
   ```

2. Verify `PYTHONPATH` includes both `nl_sql/` and project root (handled by `NLServerManager`)

3. Check that `src/utils/path_resolver.py` exists and is importable

### Error: "Port already in use"

**Symptom**: Server fails to start because port 8000 or 8001 is already in use.

**Solution**:
1. Check if servers are already running:
   ```bash
   # Check port 8000 (FastAPI)
   curl http://localhost:8000/health
   
   # Check port 8001 (MCP)
   curl http://localhost:8001/health
   ```

2. Stop existing servers:
   ```bash
   # Find and kill processes
   lsof -ti:8000 | xargs kill -9
   lsof -ti:8001 | xargs kill -9
   ```

3. Or use `NLServerManager.stop_all_servers()` if servers were started via the manager

### Error: "API key is required" when calling endpoints

**Symptom**: FastAPI server returns 400 error about missing API key.

**Cause**: API key not provided in request headers.

**Solution**:
1. Ensure API key is sent in request headers:
   ```python
   headers = {"Authorization": f"Bearer {api_key}"}
   response = requests.post(url, json=data, headers=headers)
   ```

2. Or set `OPENAI_API_KEY` environment variable before starting the server (for testing)

## Search Dialog Integration Implementation ✅ RECOMMENDED APPROACH

### Overview

**✅ This is the recommended and currently implemented approach.**

This section details the integration of the `NLQueryDialog` GUI from `tests/server_test.py` into `src/ui/dialogs/search_dialog.py`. When the user clicks on the `nl_query` radio button in the search dialog, the NL-to-SQL query interface appears as a separate non-modal dialog.

**Key Differences from Alternative Approaches**:
- Uses existing `SearchDialog` with radio button toggle
- Shows `NLQueryDialog` as separate dialog (non-modal)
- Better separation of concerns
- Easier to maintain and integrate

**Key Integration Points**:
- `NLQueryDialog` is shown as a non-modal dialog when `nl_query` radio button is selected
- Servers start when API key is submitted
- Servers stop when switching away from `nl_query` or when dialogs close
- Results are displayed in `NLQueryDialog`'s own results dialog

**See `server_implement_analysis.md`** for detailed analysis and corrections.

### Current State

**`search_dialog.py`**:
- Uses `BaseDialog` with template-based configuration
- Currently supports: `player`, `team`, `number` search options
- `nl_query` option needs to be added
- Uses `template_configs.py` to create search template
- Uses `dialog_handlers.py` for search submission logic

**`server_test.py`**:
- Contains `NLQueryDialog` class (lines 653-1098)
- Two-panel layout:
  - **Left Panel**: API key input, NL query input
  - **Right Panel**: SQL display, execute button
- Uses `NLServerManager` for server management
- Uses `NLQueryThread` for asynchronous query processing
- Displays results in a separate dialog with `QTreeWidget`

### Implementation Strategy

**Recommended Approach**: Use template's `toggle_handler` to show `NLQueryDialog` as a non-modal dialog when `nl_query` radio button is selected.

**Key Decisions**:
1. ✅ Use template `toggle_handler` instead of manual connection
2. ✅ Use `show()` instead of `exec()` for non-modal dialog
3. ✅ Stop servers when switching away from `nl_query`
4. ✅ Add cleanup in `SearchDialog.closeEvent()`

### Phase 1: Extract NLQueryDialog Module

**File**: `src/ui/dialogs/nl_query_dialog.py` (NEW)

**Action**: Extract `NLQueryDialog` and `NLQueryThread` classes from `tests/server_test.py`.

**Key Modifications**:
- Remove test-specific code (print statements, test methods)
- Make it a standalone dialog class
- Ensure proper imports from project structure
- Add proper error handling for production use

**Structure**:
```python
"""
NL-to-SQL Query Dialog for natural language database queries.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMessageBox, QHeaderView, QSizePolicy
)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from src.utils.nl_sql_server import NLServerManager
from typing import Optional
import os
import requests
import logging

logger = logging.getLogger(__name__)

class NLQueryThread(QThread):
    """Thread for sending NL query to FastAPI server."""
    finished = Signal(dict)  # {'sql': str, 'results': list}
    
    # ... (extract from server_test.py)

class NLQueryDialog(QDialog):
    """Dialog for NL-to-SQL queries."""
    
    # Signal emitted when query completes successfully
    query_completed = Signal(dict)  # {'sql': str, 'results': list}
    
    # ... (extract from server_test.py, remove test code)
```

### Phase 2: Add `nl_query` Option to Template

**File**: `src/ui/dialogs/template_configs.py`

**Change**: Add `"nl_query"` to search options and configure toggle handler.

```python
def create_search_template(
    search_handler: Callable,
    view_handler: Callable,
    clear_handler: Callable
) -> Dict[str, Any]:
    """Create template for search dialog."""
    from src.ui.dialogs.dialog_handlers import search_toggle_handler
    
    options = ["player", "team", "number", "nl_query"]  # Add nl_query
    
    template = SearchTemplate.create_template(
        title="Search Team or Player",
        search_options=options,
        search_handler=search_handler,
        view_handler=view_handler,
        clear_handler=clear_handler,
        input_label="Enter value:"
    )
    
    # Add toggle handler for nl_query
    template['selection']['toggle_handler'] = search_toggle_handler
    
    return template
```

### Phase 3: Add Toggle Handler

**File**: `src/ui/dialogs/dialog_handlers.py`

**Add `search_toggle_handler` function**:
```python
def search_toggle_handler(option: str, checked: bool, dialog):
    """Handle search type radio button toggle."""
    from src.ui.dialogs.nl_query_dialog import NLQueryDialog
    
    if checked and option == "nl_query":
        # Show NL-to-SQL dialog
        if not hasattr(dialog, '_nl_dialog') or not dialog._nl_dialog:
            dialog._nl_dialog = NLQueryDialog(parent=dialog)
        
        dialog._nl_dialog.show()  # Non-modal - doesn't block search dialog
        dialog._nl_dialog.raise_()
        dialog._nl_dialog.activateWindow()
    
    elif not checked and option == "nl_query":
        # Hide NL dialog and stop servers when switching away
        if hasattr(dialog, '_nl_dialog') and dialog._nl_dialog:
            # Stop servers before hiding
            if hasattr(dialog._nl_dialog, 'server_manager') and dialog._nl_dialog.server_manager:
                dialog._nl_dialog.server_manager.stop_all_servers()
            dialog._nl_dialog.hide()
```

### Phase 4: Initialize NL Dialog Reference

**File**: `src/ui/dialogs/search_dialog.py`

**Add to `__init__`**:
```python
def __init__(self, league, selected, stack, undo, message, parent=None):
    # ... existing code ...
    
    # Initialize NL dialog reference
    self._nl_dialog = None
```

**Add `closeEvent` handler**:
```python
def closeEvent(self, event):
    """Handle dialog close event."""
    # Stop NL query servers if dialog is open
    if hasattr(self, '_nl_dialog') and self._nl_dialog:
        if hasattr(self._nl_dialog, 'server_manager') and self._nl_dialog.server_manager:
            self._nl_dialog.server_manager.stop_all_servers()
        self._nl_dialog.close()
        self._nl_dialog = None
    
    # Call parent closeEvent
    super().closeEvent(event)
```

### Phase 5: Update Search Submit Handler

**File**: `src/ui/dialogs/dialog_handlers.py`

**Modify `search_submit_handler`**:
```python
def search_submit_handler(dialog):
    """Handle search submission."""
    selection = dialog.get_selected_option('search_type')
    
    if selection == "nl_query":
        # Show dialog if not already visible
        if hasattr(dialog, '_nl_dialog') and dialog._nl_dialog:
            dialog._nl_dialog.show()
            dialog._nl_dialog.raise_()
            dialog._nl_dialog.activateWindow()
        else:
            # Dialog not created yet - toggle handler will create it
            dialog.show_validation_error(
                "Please select 'nl_query' from the search type options to open the NL query dialog."
            )
        return
    
    # Standard search handling for player, team, number
    # ... rest of existing code ...
```

### Phase 6: Update View Handler

**File**: `src/ui/dialogs/dialog_handlers.py`

**Modify `search_view_handler`**:
```python
def search_view_handler(dialog):
    """Handle view selected search result."""
    # ... existing code ...
    
    elif search_type == "nl_query":
        # NL query results are displayed in tree widget
        dialog.show_validation_error(
            "View action is not available for natural language query results. "
            "Results are displayed in the search tree."
        )
        return
```

### Integration Workflow ✅ RECOMMENDED IMPLEMENTATION

**User Flow** (Corrected for Radio Button Toggle Implementation):
1. **User clicks Search button from main window**
   - Search dialog opens with radio buttons: player, team, number, nl_query
   - Standard search UI is visible

2. **User selects `nl_query` radio button**
   - `search_toggle_handler` is called
   - `NLQueryDialog` is created (if not exists) and shown as separate non-modal dialog
   - Two-panel layout in `NLQueryDialog`:
     - Left panel: API key input (top) and NL query input (bottom)
     - Right panel: SQL query display area (initially empty/disabled)

3. **API Key Input (Top Left in NLQueryDialog)**
   - User enters API key
   - User clicks "Submit API Key" button
   - Validate API key format
   - If valid: Start BOTH servers via `NLServerManager`, enable NL query section
   - If invalid: Show error, keep NL query disabled

4. **Natural Language Query (Bottom Left in NLQueryDialog)**
   - User enters NL query
   - User clicks "Submit NL Query" button
   - Send request to FastAPI server (port 8000)
   - Display formatted SQL on right panel
   - Enable SQL execute button

5. **SQL Execution (Right Panel in NLQueryDialog)**
   - User clicks "Execute SQL" button
   - Execute SQL query
   - Show results in separate results dialog

6. **User switches to another search type**
   - Servers stop (in toggle handler)
   - `NLQueryDialog` hides
   - Standard search UI becomes active

7. **User closes search dialog**
   - Servers stop (in `closeEvent`)
   - Resources cleaned up

**Server Lifecycle**:
- **Start**: When API key is submitted in `NLQueryDialog`
- **Stop**: When:
  - User switches away from `nl_query` (in toggle handler)
  - `NLQueryDialog` closes (in `closeEvent`)
  - `SearchDialog` closes (in `closeEvent`)

### File Changes Summary

**New Files**:
- `src/ui/dialogs/nl_query_dialog.py` - Extracted NL-to-SQL dialog

**Modified Files**:
- `src/ui/dialogs/template_configs.py` - Add `"nl_query"` to options, add toggle handler
- `src/ui/dialogs/search_dialog.py` - Initialize `_nl_dialog`, add `closeEvent` handler
- `src/ui/dialogs/dialog_handlers.py` - Add `search_toggle_handler`, update submit/view handlers

### Testing Checklist

- [ ] Click `nl_query` radio button → NL dialog appears
- [ ] Enter API key → servers start successfully
- [ ] Enter NL query → SQL is generated
- [ ] Execute SQL → results are displayed
- [ ] Switch to another search type → servers stop, NL dialog hides
- [ ] Switch back to `nl_query` → NL dialog reappears
- [ ] Close search dialog → servers stop, resources cleaned up
- [ ] Standard search (player/team/number) still works

**See `server_implement_analysis.md`** for detailed analysis, corrections, and complete implementation code.

---

## Critical Runtime Errors and Fixes

### Error 1: OpenAI Streaming API Usage Error

**Symptom**: 
```
RuntimeWarning: coroutine 'AsyncCompletions.create' was never awaited
'async for' requires an object with __aiter__ method, got coroutine
```

**Location**: `nl_sql/api_call.py` line 197

**Cause**: The code incorrectly uses `async for` directly on `client.chat.completions.create()`, which returns a coroutine, not an async iterator. The coroutine must be awaited first to get the stream object.

**Current (Incorrect) Code**:
```python
async for chunk in client.chat.completions.create(
    model=DEFAULT_MODEL,
    messages=[...],
    stream=True
):
    # Process chunk
```

**Fix**: Await the `create()` call first to get the stream:
```python
# Stream SQL generation from OpenAI
sql_query = ""
stream = await client.chat.completions.create(
    model=DEFAULT_MODEL,
    messages=[
        {"role": "system", "content": "You are a SQL expert. Generate only SQL queries, no explanations."},
        {"role": "user", "content": prompt}
    ],
    stream=True,
    temperature=0
)

async for chunk in stream:
    if chunk.choices[0].delta.content:
        content = chunk.choices[0].delta.content
        sql_query += content
        yield content
```

**Impact**: HIGH - Prevents SQL generation from working, causes server errors

---

### Error 2: MCP Server Schema Endpoint 500 Error

**Symptom**: 
```
INFO: 127.0.0.1:35848 - "GET /schema HTTP/1.1" 500 Internal Server Error
```

**Location**: `nl_sql/mcp_server.py` `/schema` endpoint

**Cause**: The `get_schema()` function may be raising an exception that's not properly handled, or the database path is incorrect.

**Potential Issues**:
1. Database file doesn't exist at the resolved path
2. Database is locked or corrupted
3. SQLite connection error
4. Exception in schema extraction logic

**Fix**: Add better error handling and validation:
```python
@app.get("/schema")
async def get_schema_endpoint():
    """Get database schema."""
    try:
        # Verify database exists
        if not DB_PATH.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Database not found: {DB_PATH}"
            )
        
        # Check if database is accessible
        try:
            test_conn = sqlite3.connect(str(DB_PATH))
            test_conn.close()
        except sqlite3.Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Cannot access database: {str(e)}"
            )
        
        # Extract schema
        schema = get_schema(DB_PATH)
        
        if not schema:
            raise HTTPException(
                status_code=500,
                detail="No schema found in database (database may be empty)"
            )
        
        return {"schema": schema, "database": str(DB_PATH)}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Database file not found: {DB_PATH}"
        )
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting schema: {str(e)}"
        )
```

**Additional Fix for `get_schema()` function**:
```python
def get_schema(db_path: Path) -> str:
    """Extract database schema for LLM consumption."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        schema_parts = []
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        if not tables:
            conn.close()
            return ""  # Empty database
        
        for (table_name,) in tables:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            if not columns:
                continue  # Skip tables with no columns
            
            # Format: table_name(column1 type, column2 type, ...)
            col_defs = []
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                col_defs.append(f"{col_name} {col_type}")
            
            schema_parts.append(f"{table_name}({', '.join(col_defs)})")
        
        conn.close()
        return "\n".join(schema_parts)
    
    except sqlite3.Error as e:
        raise Exception(f"SQLite error: {str(e)}")
    except Exception as e:
        raise Exception(f"Schema extraction error: {str(e)}")
```

**Impact**: HIGH - Prevents schema retrieval, which blocks SQL generation

---

### Error 3: Server Startup "Unknown Error"

**Symptom**:
```
[NL Server Manager] Failed to start FastAPI server process: Unknown error
[NL Server Manager] Failed to start MCP server process: Unknown error
```

**Location**: `src/utils/nl_sql_server.py` server startup

**Cause**: The `QProcess.start()` method may fail silently or the error message is not being captured properly. This can happen if:
1. Python executable path is incorrect
2. Script path is incorrect
3. Permissions issue
4. Environment variables not set correctly

**Fix**: Improve error handling in `NLServerManager`:
```python
# In start_fastapi_server() and start_mcp_server()
if server_script.exists():
    script_path = str(server_script.resolve())
    success = self.fastapi_process.start(python_exe, [script_path])
    
    if not success:
        self.fastapi_starting = False
        error_msg = self.fastapi_process.errorString()
        
        # Try to get more detailed error information
        if not error_msg or error_msg == "Unknown error":
            # Check if process actually started
            if self.fastapi_process.state() == QProcess.ProcessState.NotRunning:
                # Process failed to start - check common issues
                if not Path(python_exe).exists():
                    error_msg = f"Python executable not found: {python_exe}"
                elif not server_script.exists():
                    error_msg = f"Server script not found: {server_script}"
                else:
                    error_msg = f"Failed to start process. Check permissions and PYTHONPATH."
            else:
                error_msg = "Process started but immediately exited"
        
        print(f"[NL Server Manager] Failed to start FastAPI server process: {error_msg}")
        self.fastapi_failed.emit(f"Failed to start process: {error_msg}")
        return
```

**Impact**: MEDIUM - Makes debugging server startup issues difficult

---

## Implementation Priority

1. **CRITICAL**: Fix OpenAI streaming API usage (Error 1) - Blocks all SQL generation
2. **CRITICAL**: Fix MCP schema endpoint error handling (Error 2) - Blocks schema retrieval
3. **HIGH**: Improve server startup error reporting (Error 3) - Makes debugging easier

## Notes

- The server is designed to be lightweight and focused on SQL generation
- Streaming allows for real-time feedback to users
- SQL validation ensures database safety
- The implementation can be extended to support multiple databases or more complex queries
- **All identified errors and corrections are documented in the "Critical Errors and Corrections" and "Additional Issues and Concerns" sections above**
- **Directory structure is critical**: All server files must be in `nl_sql/` at project root, NOT in `src/servers/`
- **Runtime errors must be fixed immediately**: See "Critical Runtime Errors and Fixes" section above
- **Complete PySide6 GUI implementation plan is included in the "PySide6 GUI Implementation Plan" section**