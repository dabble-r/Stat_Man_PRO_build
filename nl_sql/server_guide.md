# NL-to-SQL Server Implementation

This directory contains the FastAPI and MCP (Model Context Protocol) server implementation for converting natural language queries to SQLite SQL queries using OpenAI.

## Architecture Overview

The system consists of two independent FastAPI servers:

1. **FastAPI Server (Port 8000)** - `api_call.py`
   - Converts natural language to SQL queries using OpenAI
   - Communicates with MCP server to get database schema
   - Validates generated SQL queries

2. **MCP Server (Port 8001)** - `mcp_server.py`
   - Implements JSON-RPC 2.0 protocol for SQLite database exploration
   - Provides database schema information
   - Executes read-only SQL queries

## File Structure

```
nl_sql/
├── api_call.py              # FastAPI server for NL-to-SQL conversion
├── mcp_server.py            # MCP server for SQLite exploration
├── start_server.py          # Startup script for FastAPI server
├── start_mcp_server.py      # Startup script for MCP server
├── start_server.sh          # Shell script to start FastAPI server
├── start_mcp_server.sh      # Shell script to start MCP server
├── ai_query.py              # GUI application (optional)
└── README.md                # This file
```

---

## FastAPI Server (api_call.py)

### Overview

The FastAPI server provides a REST API endpoint that converts natural language requests into SQLite SQL queries using OpenAI's GPT models.

**Port:** 8000  
**Base URL:** `http://localhost:8000`

### Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `openai` - OpenAI API client
- `requests` - HTTP client for MCP communication
- `pydantic` - Data validation
- `sqlite3` - Database access (standard library)

### Key Components

#### 1. Pydantic Models

**NLToSQLRequest:**
```python
class NLToSQLRequest(BaseModel):
    provider: str = "OpenAI"      # Only OpenAI is supported
    api_key: str                   # OpenAI API key
    database: str                  # Database name (e.g., "league")
    user_request: str              # Natural language query
```

**NLToSQLResponse:**
```python
class NLToSQLResponse(BaseModel):
    sql_query: str                 # Generated SQL query
    schema_context: str            # Database schema used
    validation: dict | None        # Validation results
```

#### 2. MCP Communication

**Function: `mcp_call(method: str, params: dict) -> dict`**

Makes JSON-RPC 2.0 calls to the MCP server at `http://localhost:8001/mcp`.

- **Method:** HTTP POST
- **Protocol:** JSON-RPC 2.0
- **Timeout:** 10 seconds
- **Error Handling:** 
  - Connection errors → Raises `RuntimeError` with clear message
  - Timeout errors → Raises `RuntimeError`
  - MCP errors → Raises `RuntimeError` with error message

**Example:**
```python
result = mcp_call("list_tables", {"database": "league"})
```

#### 3. Schema Retrieval

**Function: `get_schema_context(database: str) -> str`**

Retrieves database schema from MCP server with automatic fallback.

**Flow:**
1. Attempts to get schema via MCP server (`list_tables` + `get_table_schema`)
2. If MCP server unavailable → Falls back to direct SQLite access
3. Returns human-readable schema string for LLM prompt

**Fallback Function: `get_schema_context_direct(database: str) -> str`**
- Directly queries SQLite database using `PRAGMA table_info()`
- Used when MCP server is not available

#### 4. Database Path Resolution

**Function: `get_database_path_from_name(database: str) -> Path`**

Resolves database file path from database name.

**Priority:**
1. Uses `src.utils.path_resolver.get_database_path()` if available
2. Falls back to common locations:
   - `data/database/League.db`
   - `../data/database/League.db`
   - `../../data/database/League.db`

#### 5. LLM Integration

**Function: `call_llm(provider: str, api_key: str, prompt: str) -> str`**

Calls OpenAI API to generate SQL query.

- **Model:** `gpt-4o-mini` (configurable)
- **Temperature:** 0.1 (low for deterministic output)
- **Max Tokens:** 500
- **System Prompt:** "You are an expert SQL assistant. Generate only valid SQLite queries. Return ONLY the SQL query with no explanations, no markdown, no backticks."

**Function: `_call_openai(api_key: str, prompt: str) -> str`**

Internal function that:
1. Creates OpenAI client with API key
2. Sends chat completion request
3. Extracts SQL query from response
4. Cleans response (removes markdown, backticks, etc.)

**Function: `_clean_sql_response(sql_query: str) -> str`**

Cleans LLM response:
- Removes markdown code blocks (```sql ... ```)
- Strips leading/trailing whitespace
- Removes quotes if present

#### 6. Prompt Construction

**Function: `build_prompt(user_request: str, schema_context: str) -> str`**

Constructs detailed prompt for LLM with:
- User's natural language request
- Complete database schema
- Requirements (read-only, explicit columns, etc.)

#### 7. SQL Validation

**Function: `validate_sql(database: str, sql_query: str) -> dict`**

Validates generated SQL query.

**Flow:**
1. Attempts validation via MCP server (`run_query`)
2. If MCP unavailable → Falls back to direct validation
3. Returns validation result with success status, row count, columns

**Fallback Function: `validate_sql_direct(database: str, sql_query: str) -> dict`**
- Directly executes query against SQLite database
- Returns validation result

#### 8. Main Endpoint

**Endpoint: `POST /nl_to_sql`**

Converts natural language to SQL query.

**Request Body:**
```json
{
  "provider": "OpenAI",
  "api_key": "sk-...",
  "database": "league",
  "user_request": "Show me all teams"
}
```

**Response:**
```json
{
  "sql_query": "SELECT * FROM teams;",
  "schema_context": "TABLE teams:\n  - id (INTEGER)\n  - name (TEXT)\n...",
  "validation": {
    "success": true,
    "preview_row_count": 10,
    "columns": ["id", "name"],
    "types": ["INTEGER", "TEXT"]
  }
}
```

**Process Flow:**
1. Get schema context (via MCP or direct access)
2. Build prompt with schema and user request
3. Call LLM to generate SQL query
4. Clean SQL response
5. Validate SQL query (optional, non-blocking)
6. Return response

**Error Handling:**
- **400 Bad Request:** Invalid request (missing API key, unsupported provider)
- **502 Bad Gateway:** LLM API error
- **503 Service Unavailable:** MCP server unavailable
- **500 Internal Server Error:** Unexpected errors

**Additional Endpoints:**
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /openapi.json` - OpenAPI specification

---

## MCP Server (mcp_server.py)

### Overview

The MCP server implements the Model Context Protocol (JSON-RPC 2.0) for SQLite database exploration. It provides methods to list tables, get table schemas, and execute read-only queries.

**Port:** 8001  
**Base URL:** `http://localhost:8001`

### Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `sqlite3` - Database access (standard library)

### Key Components

#### 1. JSON-RPC 2.0 Models

**JSONRPCRequest:**
```python
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any                    # Request ID
    method: str                # Method name
    params: Dict[str, Any]     # Method parameters
```

**JSONRPCError:**
```python
class JSONRPCError(BaseModel):
    code: int                  # Error code
    message: str               # Error message
    data: Optional[Any]        # Additional error data
```

**JSONRPCResponse:**
```python
class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Any                    # Request ID (echoed from request)
    result: Optional[Any]      # Result (if success)
    error: Optional[JSONRPCError]  # Error (if failure)
```

#### 2. Database Path Resolution

**Function: `get_database_path_from_name(database: str) -> Path`**

Resolves database file path from database name.

**Priority:**
1. Uses `src.utils.path_resolver.get_database_path()` if available
2. Falls back to common locations:
   - `data/database/League.db`
   - `../data/database/League.db`
   - `../../data/database/League.db`
   - `data/database/{database}.db`
   - `../data/database/{database}.db`

#### 3. MCP Methods

**Method: `list_tables(database: str) -> Dict[str, Any]`**

Lists all tables in the database.

**Implementation:**
- Connects to SQLite database
- Executes: `SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'`
- Returns: `{"tables": [{"name": "table1"}, {"name": "table2"}, ...]}`

**Method: `get_table_schema(database: str, table: str) -> Dict[str, Any]`**

Gets schema information for a specific table.

**Implementation:**
- Connects to SQLite database
- Executes: `PRAGMA table_info({table})`
- Returns: `{"columns": [{"name": "col1", "type": "TEXT", "not_null": False, "default": None, "primary_key": False}, ...]}`

**Method: `run_query(database: str, sql: str) -> Dict[str, Any]`**

Executes a SQL query and returns results (read-only).

**Implementation:**
- Connects to SQLite database
- Executes SQL query
- Infers column types from first row
- Returns: `{"columns": [...], "types": [...], "rows": [[...], [...]]}`

**Error Handling:**
- SQLite errors → Raises `ValueError` with error message
- Other errors → Raises `ValueError` with error message

#### 4. JSON-RPC Handler

**Function: `handle_jsonrpc_request(request: JSONRPCRequest) -> JSONRPCResponse`**

Dispatches JSON-RPC requests to appropriate method handlers.

**Supported Methods:**
- `list_tables` → Calls `list_tables()`
- `get_table_schema` → Calls `get_table_schema()`
- `run_query` → Calls `run_query()`

**Error Codes:**
- `-32601` - Method not found
- `-32000` - Application error (ValueError)
- `-32603` - Internal error (Exception)

#### 5. FastAPI Endpoints

**Endpoint: `POST /mcp`**

Handles JSON-RPC 2.0 MCP requests.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "list_tables",
  "params": {"database": "league"}
}
```

**Response (Success):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tables": [{"name": "teams"}, {"name": "players"}]
  },
  "error": null
}
```

**Response (Error):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": null,
  "error": {
    "code": -32000,
    "message": "Failed to list tables: ..."
  }
}
```

**Additional Endpoints:**
- `GET /` - Service information
- `GET /health` - Health check (returns `{"status": "healthy"}`)

---

## Server Startup

### FastAPI Server (Port 8000)

**Script: `start_server.py`**

**Features:**
- Automatically adds `nl_sql` directory to Python path
- Verifies `uvicorn` and `api_call` can be imported
- Supports reload mode (disabled by default for subprocess execution)
- Reload can be enabled via environment variable: `STATMANG_ENABLE_RELOAD=true`

**Usage:**
```bash
# Direct execution
python start_server.py

# With reload enabled
STATMANG_ENABLE_RELOAD=true python start_server.py

# Using uvicorn directly
uvicorn api_call:app --host 0.0.0.0 --port 8000 --reload
```

**Shell Script: `start_server.sh`**
- Activates virtual environment if available
- Installs dependencies if missing
- Starts server with reload enabled

### MCP Server (Port 8001)

**Script: `start_mcp_server.py`**

**Features:**
- Automatically adds `nl_sql` directory to Python path
- Verifies `uvicorn` and `mcp_server` can be imported
- Supports reload mode (disabled by default for subprocess execution)
- Reload can be enabled via environment variable: `STATMANG_ENABLE_RELOAD=true`

**Usage:**
```bash
# Direct execution
python start_mcp_server.py

# With reload enabled
STATMANG_ENABLE_RELOAD=true python start_mcp_server.py

# Using uvicorn directly
uvicorn mcp_server:app --host 0.0.0.0 --port 8001 --reload
```

**Shell Script: `start_mcp_server.sh`**
- Activates virtual environment if available
- Installs dependencies if missing
- Starts server with reload enabled

---

## Integration with GUI

The servers are designed to be started automatically by the GUI application using `src.utils.nl_sql_server.NLServerManager`. The manager:

1. Starts both servers as subprocesses using `QProcess`
2. Monitors server output and errors
3. Verifies servers are ready by checking health endpoints
4. Provides signals for server status updates
5. Handles server shutdown gracefully

**Server Manager Usage:**
```python
from src.utils.nl_sql_server import NLServerManager

manager = NLServerManager(parent)
manager.start_fastapi_server()
manager.start_mcp_server()
```

---

## Error Handling & Fallbacks

### FastAPI Server Fallbacks

1. **MCP Server Unavailable:**
   - Schema retrieval → Falls back to direct SQLite access
   - SQL validation → Falls back to direct SQLite validation
   - Errors are logged but don't block the request

2. **Database Path Resolution:**
   - Primary: Uses `src.utils.path_resolver.get_database_path()`
   - Fallback: Tries common database locations

3. **OpenAI API Errors:**
   - Returns HTTP 502 with error message
   - Logs full error traceback

### MCP Server Error Handling

1. **Database Not Found:**
   - Returns JSON-RPC error with code -32000
   - Error message: "Could not find database file for '{database}'"

2. **SQL Errors:**
   - Returns JSON-RPC error with code -32000
   - Error message includes SQLite error details

3. **Method Not Found:**
   - Returns JSON-RPC error with code -32601
   - Error message: "Method not found: {method}"

---

## Logging

Both servers use Python's `logging` module with INFO level.

**FastAPI Server Logs:**
- Request received
- Schema retrieval attempts
- LLM API calls
- SQL validation results
- Errors with full tracebacks

**MCP Server Logs:**
- MCP requests received
- Method execution
- Database operations
- Errors with full tracebacks

---

## Security Considerations

1. **API Keys:**
   - OpenAI API keys are passed in request body (not stored)
   - Keys are not logged

2. **SQL Injection:**
   - MCP server executes queries directly (read-only)
   - FastAPI server validates queries before execution
   - Only SELECT queries are recommended (enforced in prompt)

3. **Database Access:**
   - Read-only access recommended
   - No DROP, ALTER, or CREATE operations in generated queries

---

## Testing

### Test FastAPI Server

```bash
# Start server
python start_server.py

# Test endpoint
curl -X POST "http://localhost:8000/nl_to_sql" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "OpenAI",
    "api_key": "sk-...",
    "database": "league",
    "user_request": "Show me all teams"
  }'
```

### Test MCP Server

```bash
# Start server
python start_mcp_server.py

# Test endpoint
curl -X POST "http://localhost:8001/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "list_tables",
    "params": {"database": "league"}
  }'
```

### Health Checks

```bash
# FastAPI server
curl http://localhost:8000/docs

# MCP server
curl http://localhost:8001/health
```

---

## Troubleshooting

### Server Won't Start

**Error: "uvicorn is not installed"**
```bash
pip install uvicorn fastapi
```

**Error: "Failed to import api_call" or "Failed to import mcp_server"**
- Ensure you're running from the `nl_sql` directory
- Check that all dependencies are installed
- Verify Python path includes `nl_sql` directory

### Connection Errors

**Error: "Connection refused" to MCP server**
- Ensure MCP server is running on port 8001
- FastAPI server will fall back to direct database access
- Check firewall settings

**Error: "Failed to connect to SQLite Explorer MCP server"**
- MCP server may not be running
- System will automatically fall back to direct database access
- Check MCP server logs for errors

### Database Errors

**Error: "Could not find database file"**
- Verify database file exists
- Check database path resolution logic
- Ensure `src.utils.path_resolver` is available or database is in expected location

---

## Dependencies

### Required Packages

```txt
fastapi>=0.100.0
uvicorn>=0.20.0
openai>=1.0.0
requests>=2.31.0
pydantic>=2.0.0
```

### Installation

```bash
pip install fastapi uvicorn openai requests pydantic
```

Or from project requirements:
```bash
pip install -r ../requirements.txt
```

---

## Configuration

### Environment Variables

- `STATMANG_ENABLE_RELOAD` - Enable auto-reload for development (default: `false`)
  - Set to `true` to enable reload mode
  - Useful for development, disabled by default for subprocess execution

### Port Configuration

- FastAPI Server: Port 8000 (hardcoded in `api_call.py` and `start_server.py`)
- MCP Server: Port 8001 (hardcoded in `mcp_server.py` and `start_mcp_server.py`)

To change ports, modify:
- Server startup scripts (`start_server.py`, `start_mcp_server.py`)
- Server files (`api_call.py`, `mcp_server.py`)
- `SQLITE_MCP_URL` in `api_call.py` (if changing MCP port)

---

## API Documentation

### FastAPI Server

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### MCP Server

MCP server follows JSON-RPC 2.0 specification. See method descriptions above for details.

---

## Development Notes

1. **Reload Mode:**
   - Disabled by default when run as subprocess (e.g., from GUI)
   - Enabled via `STATMANG_ENABLE_RELOAD=true` environment variable
   - Reload uses multiprocessing which can cause issues in subprocess execution

2. **Path Resolution:**
   - Both servers add project root to `sys.path` for imports
   - Database path resolution uses `src.utils.path_resolver` if available
   - Fallback paths are relative to server startup location

3. **Error Handling:**
   - All errors are logged with full tracebacks
   - HTTP errors return appropriate status codes
   - JSON-RPC errors follow JSON-RPC 2.0 specification

---

## License

Part of the stat_test_build project.
