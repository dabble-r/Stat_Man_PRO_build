"""
FastAPI Server for NL-to-SQL Conversion (Port 8000)

This server handles:
- Natural language to SQL conversion using OpenAI
- SQL validation using sqlglot
- Query execution via MCP server
- Streaming responses

Requires API key via Authorization header.
"""

import sqlite3
import asyncio
import os
import sys
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
import sqlglot
from sqlglot import expressions as exp
import requests
import httpx

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.path_resolver import get_database_path, get_app_base_path
from src.visualization.nl_plot_pipeline import build_chart_config_prompt, parse_chart_config
from src.utils.nl_plot_log import get_nl_plot_logger

app = FastAPI(title="NL-to-SQL Server", version="1.0.0")

# Get database path
DB_PATH = get_database_path()

# MCP server URL
MCP_SERVER_URL = "http://localhost:8001"

# Default model
DEFAULT_MODEL = "gpt-4o-mini"

# Cache for pre-loaded schema (initialized on startup)
_cached_schema: Optional[str] = None

# Setup file logging for FastAPI application
_logger_initialized = False
_app_logger: Optional[logging.Logger] = None

def _setup_app_logging():
    """Setup file logging for FastAPI application. Issue 7: when frozen use writable app base for logs; do not crash on failure."""
    global _logger_initialized, _app_logger
    
    if _logger_initialized:
        return _app_logger
    
    _app_logger = logging.getLogger("fastapi_app")
    _app_logger.setLevel(logging.DEBUG)
    _app_logger.handlers.clear()
    _app_logger.propagate = False
    
    try:
        # Logs under data/logs (app base in dev or frozen)
        logs_dir = Path(get_app_base_path()) / "data" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        app_log_file = logs_dir / "fastapi_app.log"
        app_handler = logging.FileHandler(app_log_file, mode='a', encoding='utf-8')
        app_handler.setLevel(logging.DEBUG)
        app_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        app_handler.setFormatter(app_formatter)
        _app_logger.addHandler(app_handler)
        _app_logger.info("=" * 80)
        _app_logger.info(f"FastAPI Application Logging Initialized - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        import sys as _sys
        _sys.stderr.write(f"[FastAPI app] Could not setup file logging: {e}\n")
        # _app_logger has no FileHandler; _log_print will still work for level, but file won't be written
    _logger_initialized = True
    return _app_logger

# Initialize logging on module import
_setup_app_logging()

def _log_print(level: str, message: str):
    """Log message to both file and print to stdout."""
    if _app_logger:
        if level == "INFO":
            _app_logger.info(message)
        elif level == "ERROR":
            _app_logger.error(message)
        elif level == "WARNING":
            _app_logger.warning(message)
        elif level == "DEBUG":
            _app_logger.debug(message)
    print(message)


class QueryRequest(BaseModel):
    """Request model for NL query."""
    question: str
    api_key: Optional[str] = None  # Optional, prefer Authorization header


class ChartConfigRequest(BaseModel):
    """Request model for NL to chart config."""
    description: str
    columns: List[str]
    dtypes: Optional[Dict[str, str]] = None


def get_api_key_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def get_api_key(
    authorization: Optional[str] = Depends(get_api_key_from_header)
) -> str:
    """
    Get API key from header or environment (for endpoints that don't have a request body with api_key).
    Use get_api_key_for_query for /nl_to_sql which allows body fallback.
    """
    api_key = authorization
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API key required. Provide via Authorization header (Bearer <key>) or set OPENAI_API_KEY."
        )
    return api_key


def get_api_key_for_query(
    request: QueryRequest,
    authorization: Optional[str] = Depends(get_api_key_from_header)
) -> str:
    """
    Get API key from request (header preferred, body fallback, then environment).
    Only use with endpoints that have QueryRequest body (e.g. /nl_to_sql).
    """
    api_key = authorization
    if not api_key and request.api_key:
        api_key = request.api_key
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API key required. Provide via Authorization header (Bearer <key>) or request body."
        )
    return api_key


def clean_sql(sql: str) -> str:
    """
    Clean SQL query by removing markdown code blocks and extra whitespace.
    
    Args:
        sql: Raw SQL string (may contain markdown formatting)
        
    Returns:
        str: Cleaned SQL query
    """
    if not sql:
        return ""
    
    # Remove markdown code blocks (```sql ... ``` or ``` ... ```)
    # Pattern matches: ```sql, ```SQL, ```, etc. at start, and ``` at end
    sql = re.sub(r'^```\w*\s*\n?', '', sql, flags=re.MULTILINE | re.IGNORECASE)
    sql = re.sub(r'\n?\s*```\s*$', '', sql, flags=re.MULTILINE)
    
    # Remove leading/trailing whitespace
    sql = sql.strip()
    
    # Remove any remaining markdown formatting (like "sql" prefix)
    # Only remove if it's at the very start and followed by whitespace or newline
    sql = re.sub(r'^sql\s+', '', sql, flags=re.IGNORECASE)
    
    return sql.strip()


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Validate SQL query for safety and correctness.
    
    Args:
        sql: SQL query string (may contain markdown formatting)
        
    Returns:
        tuple: (is_valid, validated_sql_or_error_message)
               If valid: (True, validated_sql)
               If invalid: (False, error_message)
    """
    try:
        # Clean SQL first (remove markdown code blocks)
        cleaned_sql = clean_sql(sql)
        
        if not cleaned_sql:
            return False, "Empty SQL query"
        
        # Parse SQL
        parsed = sqlglot.parse_one(cleaned_sql, read="sqlite")
        
        if not parsed:
            return False, f"Invalid SQL syntax. Could not parse: {cleaned_sql[:100]}"
        
        # Check for dangerous operations
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        sql_upper = cleaned_sql.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Dangerous operation detected: {keyword}. Only SELECT queries are allowed."
        
        # Check if it's a SELECT statement
        if not isinstance(parsed, exp.Select):
            return False, f"Only SELECT queries are allowed. Got: {type(parsed).__name__}"
        
        # Check for LIMIT clause (recommended but not strictly required)
        has_limit = any(isinstance(node, exp.Limit) for node in parsed.walk())
        validated_sql = cleaned_sql
        if not has_limit:
            # Add LIMIT if missing (safety measure)
            validated_sql = f"{cleaned_sql.rstrip(';')} LIMIT 100"
        
        return True, validated_sql
    except Exception as e:
        return False, f"SQL validation error: {str(e)}"


async def get_database_schema(use_cache: bool = True) -> str:
    """
    Get database schema from MCP server.
    
    Args:
        use_cache: If True, use cached schema if available (faster)
    
    Returns:
        str: Database schema, or fallback schema if database is empty
    """
    global _cached_schema
    
    # Return cached schema if available and caching is enabled
    if use_cache and _cached_schema is not None:
        return _cached_schema
    
    try:
        response = requests.get(f"{MCP_SERVER_URL}/schema", timeout=5)
        if response.status_code == 200:
            schema = response.json().get("schema", "")
            
            # If schema is empty, provide fallback schema based on expected structure
            if not schema or not schema.strip():
                schema = get_fallback_schema()
            
            # Cache the schema for future requests
            _cached_schema = schema
            return schema
        else:
            # MCP server unavailable, use fallback
            schema = get_fallback_schema()
            _cached_schema = schema
            return schema
    except Exception:
        # MCP server unavailable, use fallback
        schema = get_fallback_schema()
        _cached_schema = schema
        return schema


def get_fallback_schema() -> str:
    """
    Get fallback schema when database is empty or schema unavailable.
    
    This provides the expected schema structure for League.db based on the codebase.
    
    Returns:
        str: Fallback schema description
    """
    return """league(leagueID INTEGER, name TEXT, commissioner TEXT, treasurer TEXT, communications TEXT, historian TEXT, recruitment TEXT, start TEXT, stop TEXT)
team(teamID INTEGER, name TEXT, leagueID INTEGER, league TEXT, logo TEXT, manager TEXT, players TEXT, lineup TEXT, positions TEXT, wins INTEGER, losses INTEGER, games_played INTEGER, wl_avg REAL, bat_avg REAL, team_era REAL, max_roster INTEGER)
player(playerID INTEGER, name TEXT, leagueID INTEGER, teamID INTEGER, number INTEGER, team TEXT, positions TEXT, pa INTEGER, at_bat INTEGER, fielder_choice INTEGER, hit INTEGER, bb INTEGER, hbp INTEGER, put_out INTEGER, so INTEGER, hr INTEGER, rbi INTEGER, runs INTEGER, singles INTEGER, doubles INTEGER, triples INTEGER, sac_fly INTEGER, OBP REAL, BABIP REAL, SLG REAL, AVG REAL, ISO REAL, image TEXT)
pitcher(playerID INTEGER, name TEXT, leagueID INTEGER, teamID INTEGER, number INTEGER, team TEXT, positions TEXT, wins INTEGER, losses INTEGER, games_played INTEGER, games_started INTEGER, games_completed INTEGER, shutouts INTEGER, saves INTEGER, save_ops INTEGER, ip REAL, p_at_bats INTEGER, p_hits INTEGER, p_runs INTEGER, er INTEGER, p_hr INTEGER, p_hb INTEGER, p_bb INTEGER, p_so INTEGER, WHIP REAL, p_avg REAL, k_9 REAL, bb_9 REAL, era REAL)"""


@app.on_event("startup")
async def startup_event():
    """
    Pre-initialize endpoint on server startup.
    
    This eliminates the cold start delay by pre-loading:
    - Database schema from MCP server
    - Fallback schema if MCP server is unavailable
    
    This makes the first request to /nl_to_sql much faster.
    """
    print("[FastAPI Startup] Pre-initializing database schema...")
    try:
        # Pre-load database schema (this will cache it)
        schema = await get_database_schema(use_cache=False)
        if schema:
            print(f"[FastAPI Startup] Schema loaded successfully ({len(schema)} chars)")
        else:
            print("[FastAPI Startup] Using fallback schema")
    except Exception as e:
        print(f"[FastAPI Startup] Warning: Could not pre-load schema: {e}")
        print("[FastAPI Startup] Will use fallback schema on first request")
    print("[FastAPI Startup] Initialization complete")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "NL-to-SQL Server"}


@app.post("/mcp/ask")
async def ask_nl_query(
    request: QueryRequest,
    api_key: str = Depends(get_api_key_for_query)
):
    """
    Convert natural language query to SQL and execute it.
    
    Args:
        request: Query request with natural language question
        api_key: OpenAI API key (from header or request)
        
    Returns:
        StreamingResponse: Streamed SQL query and results
    """
    async def generate_response():
        try:
            # Get database schema
            schema = await get_database_schema()
            
            # Create OpenAI client
            client = AsyncOpenAI(api_key=api_key)
            
            # Build prompt for LLM
            schema_note = ""
            if not schema or not schema.strip() or schema.strip() == "sqlite_sequence(sqlite_sequence)":
                schema_note = "\n⚠️ Note: Database appears to be empty. Using expected schema structure."
                schema = get_fallback_schema()
            
            prompt = f"""You are a SQL expert. Convert the following natural language question into a SQLite SQL query.

Database Schema:
{schema}{schema_note}

CRITICAL: Use EXACT table names from schema above:
- Table name is "team" (singular, NOT "teams")
- Table name is "player" (singular, NOT "players")  
- Table name is "pitcher" (singular, NOT "pitchers")
- Table name is "league" (singular, NOT "leagues")

Rules:
1. Only generate SELECT queries
2. Always include a LIMIT clause (default to 100 if not specified)
3. Use proper SQLite syntax
4. Use EXACT table names from schema (singular forms: team, player, pitcher, league)
5. Return ONLY the SQL query, no explanations, no markdown code blocks, no backticks
6. Do NOT wrap the query in ```sql or any other markdown formatting
7. Return the raw SQL query only

Question: {request.question}

SQL Query:"""
            
            # Stream SQL generation from OpenAI
            # Await the create() call first to get the stream object
            sql_query = ""
            stream = await client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Generate only SQL queries, no explanations, no markdown formatting, no code blocks. Return raw SQL only."},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                temperature=0
            )
            
            # Now iterate over the stream
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    sql_query += content
                    yield content
            
            # Validate SQL
            is_valid, result = validate_sql(sql_query)
            
            if not is_valid:
                yield f"\n\n---\n\nERROR: {result}\n"
                return
            
            # Use validated SQL (may have LIMIT added)
            sql_query = result
            
            # Execute query via MCP server
            yield "\n\n---\n\nRESULTS:\n"
            
            try:
                response = requests.post(
                    f"{MCP_SERVER_URL}/execute",
                    json={"sql": sql_query},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    results = result_data.get("results", [])
                    
                    if results:
                        # Print column headers
                        if results:
                            headers = list(results[0].keys())
                            yield " | ".join(headers) + "\n"
                            yield "-" * (len(" | ".join(headers))) + "\n"
                            
                            # Print rows
                            for row in results:
                                values = [str(row.get(h, "")) for h in headers]
                                yield " | ".join(values) + "\n"
                    else:
                        yield "No results found.\n"
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    yield f"ERROR: {error_detail}\n"
            except requests.exceptions.RequestException as e:
                yield f"ERROR: Failed to execute query: {str(e)}\n"
        
        except Exception as e:
            yield f"ERROR: {str(e)}\n"
    
    return StreamingResponse(generate_response(), media_type="text/plain")


@app.post("/nl_to_sql")
async def nl_to_sql(
    request: QueryRequest,
    api_key: str = Depends(get_api_key_for_query)
):
    """
    Convert natural language query to SQL ONLY (does not execute).
    
    Args:
        request: Query request with natural language question
        api_key: OpenAI API key (from header or request)
        
    Returns:
        JSON with SQL query string
    """
    import traceback
    
    try:
        # Log API key status (without exposing full key)
        api_key_preview = f"{api_key[:7]}...{api_key[-4:]}" if api_key and len(api_key) > 11 else "None"
        print(f"[NL-to-SQL] Step 1: Received request with API key: {api_key_preview}")
        print(f"[NL-to-SQL] Step 1: Question: {request.question[:100]}...")
        
        # Validate API key format
        if not api_key or not api_key.startswith("sk-"):
            error_msg = f"Invalid API key format. OpenAI API keys should start with 'sk-'. Got: {api_key_preview}"
            print(f"[NL-to-SQL] ERROR: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Get database schema
        print(f"[NL-to-SQL] Step 2: Getting database schema...")
        schema = await get_database_schema()
        print(f"[NL-to-SQL] Step 2: Schema loaded ({len(schema)} chars)")
        
        # Create OpenAI client with explicit timeout and connection settings
        print(f"[NL-to-SQL] Step 3: Creating OpenAI client...")
        print(f"[NL-to-SQL] Step 3: API Key Info:")
        print(f"  - Length: {len(api_key) if api_key else 0}")
        print(f"  - Preview: {api_key[:7] if api_key else 'None'}...{api_key[-4:] if api_key and len(api_key) > 11 else ''}")
        print(f"  - Format valid: {api_key.startswith('sk-') if api_key else False}")
        
        try:
            # Explicit base URL to ensure correct endpoint
            base_url = "https://api.openai.com/v1"
            
            # Create HTTP client with explicit configuration
            # Use context manager to ensure proper cleanup
            # Increased timeouts to handle slow connections and proxy delays
            # Read timeout increased to 120s for slow responses
            # Connect timeout increased to 30s for proxy/SSL handshake delays
            http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0, read=120.0, write=20.0, pool=20.0),
                verify=True,  # Explicit SSL verification
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
            # Add proxy support if configured
            proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("https_proxy") or os.getenv("http_proxy")
            if proxy_url:
                print(f"[NL-to-SQL] Step 3: Using proxy: {proxy_url}")
                http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(120.0, connect=30.0, read=120.0, write=20.0, pool=20.0),
                    verify=True,
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                    proxies={"https://": proxy_url, "http://": proxy_url}
                )
            
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client,
                max_retries=2
            )
            print(f"[NL-to-SQL] Step 3: OpenAI client created successfully")
            print(f"[NL-to-SQL] Step 3: Base URL: {base_url}")
        except Exception as e:
            error_msg = f"Failed to create OpenAI client: {str(e)}"
            print(f"[NL-to-SQL] ERROR: {error_msg}")
            print(f"[NL-to-SQL] ERROR traceback:\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Build prompt for LLM
        schema_note = ""
        if not schema or not schema.strip() or schema.strip() == "sqlite_sequence(sqlite_sequence)":
            schema_note = "\n⚠️ Note: Database appears to be empty. Using expected schema structure."
            schema = get_fallback_schema()
        
        prompt = f"""You are a SQL expert. Convert the following natural language question into a SQLite SQL query.

Database Schema:
{schema}{schema_note}

CRITICAL: Use EXACT table names from schema above:
- Table name is "team" (singular, NOT "teams")
- Table name is "player" (singular, NOT "players")  
- Table name is "pitcher" (singular, NOT "pitchers")
- Table name is "league" (singular, NOT "leagues")

Rules:
1. Only generate SELECT queries
2. Always include a LIMIT clause (default to 100 if not specified)
3. Use proper SQLite syntax
4. Use EXACT table names from schema (singular forms: team, player, pitcher, league)
5. Return ONLY the SQL query, no explanations, no markdown code blocks, no backticks
6. Do NOT wrap the query in ```sql or any other markdown formatting
7. Return the raw SQL query only

Question: {request.question}

SQL Query:"""
        
        # Generate SQL from OpenAI (non-streaming for simplicity)
        print(f"[NL-to-SQL] Step 4: Sending request to OpenAI API (model: {DEFAULT_MODEL})...")
        print(f"[NL-to-SQL] Step 4: Prompt length: {len(prompt)} chars")
        print(f"[NL-to-SQL] Step 4: Request details:")
        print(f"  - Model: {DEFAULT_MODEL}")
        print(f"  - Max tokens: 500")
        print(f"  - Temperature: 0")
        
        try:
            # Use httpx.Timeout configured in client (no need for asyncio.wait_for wrapper)
            # The httpx.Timeout(60.0, connect=15.0, read=60.0) already handles timeouts
            print(f"[NL-to-SQL] Step 4: Calling OpenAI API...")
            response = await client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Generate only SQL queries, no explanations, no markdown formatting, no code blocks. Return raw SQL only."},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                temperature=0,
                max_tokens=500
            )
            print(f"[NL-to-SQL] Step 5: SUCCESS - Received response from OpenAI API")
            print(f"[NL-to-SQL] Step 5: Response has {len(response.choices)} choices")
        except httpx.TimeoutException as e:
            error_msg = f"OpenAI API call timed out: {str(e)}"
            print(f"[NL-to-SQL] ERROR: {error_msg}")
            print(f"[NL-to-SQL] ERROR: Timeout occurred - connection or read timeout exceeded")
            raise HTTPException(status_code=504, detail=error_msg)
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Enhanced error diagnostics for connection errors
            if "Connection" in error_type or "connection" in error_msg.lower() or "connect" in error_msg.lower():
                print(f"[NL-to-SQL] Connection error detected. Diagnosing network issue...")
                
                # Test network connectivity
                import socket
                network_ok = False
                dns_ok = False
                try:
                    # Test DNS resolution
                    socket.gethostbyname("api.openai.com")
                    dns_ok = True
                    print(f"[NL-to-SQL] DNS resolution: OK")
                    
                    # Test TCP connection
                    sock = socket.create_connection(("api.openai.com", 443), timeout=5)
                    sock.close()
                    network_ok = True
                    print(f"[NL-to-SQL] TCP connection to api.openai.com:443: OK")
                except socket.gaierror as dns_err:
                    dns_ok = False
                    print(f"[NL-to-SQL] DNS resolution failed: {dns_err}")
                except (socket.timeout, OSError, ConnectionRefusedError) as conn_err:
                    network_ok = False
                    print(f"[NL-to-SQL] TCP connection failed: {conn_err}")
                
                # Build detailed error message
                if not dns_ok:
                    error_msg = f"OpenAI API connection error: DNS resolution failed. Cannot resolve api.openai.com. Check network/DNS settings."
                elif not network_ok:
                    error_msg = f"OpenAI API connection error: Cannot connect to api.openai.com:443. Check firewall/proxy settings. Original error: {error_msg}"
                else:
                    error_msg = f"OpenAI API connection error: {error_msg}. Network appears reachable, but API call failed."
            else:
                error_msg = f"OpenAI API error: {error_msg}"
            
            print(f"[NL-to-SQL] ERROR: {error_msg}")
            print(f"[NL-to-SQL] ERROR type: {error_type}")
            print(f"[NL-to-SQL] ERROR traceback:\n{traceback.format_exc()}")
            raise HTTPException(status_code=502, detail=error_msg)
        
        if not response.choices or not response.choices[0].message.content:
            error_msg = "OpenAI API returned empty response"
            print(f"[NL-to-SQL] ERROR: {error_msg}")
            raise HTTPException(status_code=502, detail=error_msg)
        
        sql_query = response.choices[0].message.content.strip()
        print(f"[NL-to-SQL] Step 6: Raw SQL from OpenAI: {sql_query[:100]}...")
        
        # Clean SQL (remove markdown if present)
        sql_query = clean_sql(sql_query)
        print(f"[NL-to-SQL] Step 7: Cleaned SQL: {sql_query[:100]}...")
        
        # Validate SQL
        print(f"[NL-to-SQL] Step 8: Validating SQL...")
        is_valid, validated_sql = validate_sql(sql_query)
        
        if not is_valid:
            error_msg = f"Invalid SQL generated: {validated_sql}"
            print(f"[NL-to-SQL] ERROR: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        print(f"[NL-to-SQL] Step 9: SQL validated successfully")
        print(f"[NL-to-SQL] Step 9: Final SQL: {validated_sql[:100]}...")
        
        return {"sql": validated_sql}
    
    except HTTPException:
        raise
    except Exception as e:
        # Catch ALL exceptions to prevent server crash
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[NL-to-SQL] CRITICAL ERROR: {error_type}: {error_msg}")
        print(f"[NL-to-SQL] CRITICAL ERROR traceback:\n{traceback.format_exc()}")
        
        # Return error response instead of crashing
        # This prevents server from being killed (SIGKILL)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error generating SQL: {error_type}: {error_msg}"
        )


@app.post("/nl_to_chart_config")
async def nl_to_chart_config(
    request: ChartConfigRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Convert natural language plot description to chart options dict.

    Request: description (str), columns (list of column names), optional dtypes (dict).
    Returns: JSON object with chart_type, x_col, y_col, series_col, title, etc. for build_figure().
    """
    log = get_nl_plot_logger()
    log.info("--- NL-plot request ---")
    log.info("natural_language_query: %s", request.description)
    log.info("request_body: %s", json.dumps({"description": request.description, "columns": request.columns, "dtypes": request.dtypes or {}}))
    try:
        if not api_key or not api_key.startswith("sk-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid API key format. OpenAI API keys should start with 'sk-'."
            )
        if not request.columns:
            raise HTTPException(status_code=400, detail="columns list cannot be empty")

        prompt = build_chart_config_prompt(
            request.description,
            request.columns,
            request.dtypes
        )
        log.info("prompt (formatted):\n%s", prompt)

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You output only a JSON object for chart configuration. No markdown, no explanation."},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=0,
            max_tokens=400
        )

        if not response.choices or not response.choices[0].message.content:
            raise HTTPException(status_code=502, detail="OpenAI returned empty response")

        content = response.choices[0].message.content.strip()
        log.info("llm_raw_response: %s", content)
        options = parse_chart_config(content, request.columns)
        log.info("chart_config_output: %s", json.dumps(options, indent=2))
        log.info("nl_to_chart_config success chart_type=%s", options.get("chart_type"))
        return options

    except HTTPException:
        raise
    except ValueError as e:
        log.warning("nl_to_chart_config validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("nl_to_chart_config error")
        log.warning("nl_to_chart_config error_detail: %s", str(e))
        raise HTTPException(status_code=502, detail=f"Chart config error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
