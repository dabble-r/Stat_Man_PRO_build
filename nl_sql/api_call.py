from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import textwrap
import re
import traceback
import logging
import sqlite3
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Import OpenAI (required dependency)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    # Don't raise here - let the endpoint handle it when actually called
    # This allows the server to start even if OpenAI isn't installed yet

# URL of the SQLite Explorer MCP server
SQLITE_MCP_URL = "http://localhost:8001/mcp"

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.utils.path_resolver import get_database_path
    PATH_RESOLVER_AVAILABLE = True
except ImportError:
    PATH_RESOLVER_AVAILABLE = False
    logger.warning("Could not import path_resolver, will use fallback database path resolution")


# ---------- Models ----------

class NLToSQLRequest(BaseModel):
    provider: str = "OpenAI"  # Only OpenAI is supported
    api_key: str
    database: str          # e.g. "localdb"
    user_request: str      # natural language description


class NLToSQLResponse(BaseModel):
    sql_query: str
    schema_context: str
    validation: dict | None = None


# ---------- MCP helper to talk to SQLite Explorer ----------

def mcp_call(method: str, params: dict) -> dict:
    """Make a JSON-RPC 2.0 call to the SQLite Explorer MCP server."""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        resp = requests.post(SQLITE_MCP_URL, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Check if there's an actual error (not just the key existing with None value)
        if "error" in data and data["error"] is not None:
            error_obj = data.get("error", {})
            if isinstance(error_obj, dict):
                error_msg = error_obj.get("message", str(error_obj))
            else:
                error_msg = str(error_obj)
            raise RuntimeError(f"MCP error: {error_msg}")
        # Return result if present, otherwise return the whole response
        return data.get("result", data)
    except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
        # Re-raise as RuntimeError with clear message
        raise RuntimeError(
            f"Failed to connect to SQLite Explorer MCP server at {SQLITE_MCP_URL}. "
            "Make sure the MCP server is running on port 8001."
        ) from e
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Timeout connecting to SQLite Explorer MCP server at {SQLITE_MCP_URL}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error communicating with MCP server: {str(e)}") from e


def get_database_path_from_name(database: str) -> Path:
    """Get the actual database file path from database name."""
    if PATH_RESOLVER_AVAILABLE:
        # Use the path resolver if available
        db_path = get_database_path()
        if db_path.exists():
            return db_path
    # Fallback: try common locations
    possible_paths = [
        Path("data/database/League.db"),
        Path("../data/database/League.db"),
        Path("../../data/database/League.db"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    raise RuntimeError(f"Could not find database file for '{database}'")


def get_schema_context_direct(database: str) -> str:
    """
    Get schema context by querying SQLite database directly.
    Fallback when MCP server is not available.
    """
    try:
        db_path = get_database_path_from_name(database)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_lines = []
        
        for table_name in tables:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema_lines.append(f"TABLE {table_name}:")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                schema_lines.append(f"  - {col_name} ({col_type or 'UNKNOWN'})")
            schema_lines.append("")  # blank line between tables
        
        conn.close()
        return "\n".join(schema_lines)
    except Exception as e:
        raise RuntimeError(f"Failed to get schema directly from database: {str(e)}") from e


def get_schema_context(database: str) -> str:
    """
    Ask SQLite Explorer MCP for:
      - tables in the database
      - schema for each table
    Return a human-readable schema summary string for the LLM prompt.
    
    Falls back to direct SQLite query if MCP server is unavailable.
    """
    try:
        # Try MCP server first
        logger.info(f"Attempting to get schema via MCP server for database: {database}")
        # 1. List tables
        tables_result = mcp_call("list_tables", {"database": database})
        tables = tables_result.get("tables", [])

        schema_lines = []
        
        # Handle empty database case
        if not tables:
            logger.warning(f"No tables found in database '{database}' - database may be empty")
            return "DATABASE SCHEMA:\n  (No tables found in database)"

        for table in tables:
            table_name = table["name"]
            schema_result = mcp_call("get_table_schema", {
                "database": database,
                "table": table_name
            })
            columns = schema_result.get("columns", [])
            schema_lines.append(f"TABLE {table_name}:")
            for col in columns:
                col_name = col["name"]
                col_type = col.get("type", "UNKNOWN")
                schema_lines.append(f"  - {col_name} ({col_type})")
            schema_lines.append("")  # blank line between tables

        logger.info("Successfully retrieved schema via MCP server")
        return "\n".join(schema_lines)
    except RuntimeError as e:
        # MCP server unavailable - fall back to direct database access
        error_msg = str(e)
        if "Failed to connect" in error_msg or "Connection refused" in error_msg:
            logger.warning(f"MCP server unavailable ({error_msg}), falling back to direct database access")
            try:
                schema = get_schema_context_direct(database)
                logger.info("Successfully retrieved schema via direct database access")
                return schema
            except Exception as fallback_error:
                raise RuntimeError(
                    f"MCP server unavailable and direct database access failed: {str(fallback_error)}. "
                    f"Original MCP error: {error_msg}"
                ) from fallback_error
        else:
            # Re-raise other RuntimeErrors
            raise


# ---------- LLM call with provider support ----------

def call_llm(provider: str, api_key: str, prompt: str) -> str:
    """
    Call OpenAI to generate SQL query from natural language prompt.
    
    Args:
        provider: LLM provider name (must be "OpenAI")
        api_key: OpenAI API key
        prompt: Full prompt with schema context and user request
        
    Returns:
        str: Generated SQL query
        
    Raises:
        ValueError: If provider is not OpenAI or API key is invalid
        RuntimeError: If API call fails
    """
    global OpenAI, OPENAI_AVAILABLE
    
    provider_lower = provider.lower()
    
    if provider_lower != "openai":
        raise ValueError(f"Only OpenAI is supported. Received: {provider}")
    
    if not OPENAI_AVAILABLE:
        # Try to import again in case it was installed after server start
        try:
            from openai import OpenAI
            OPENAI_AVAILABLE = True
        except ImportError:
            raise ValueError("OpenAI package not installed. Install with: pip install openai")
    
    return _call_openai(api_key, prompt)


def _call_openai(api_key: str, prompt: str) -> str:
    """Call OpenAI API to generate SQL query."""
    try:
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using cost-effective model, can be changed to gpt-4
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert SQL assistant. Generate only valid SQLite queries. Return ONLY the SQL query with no explanations, no markdown, no backticks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for more deterministic SQL generation
            max_tokens=500
        )
        
        sql_query = response.choices[0].message.content.strip()
        
        # Clean up the response - remove markdown code blocks if present
        sql_query = _clean_sql_response(sql_query)
        
        return sql_query
        
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {str(e)}")


def _clean_sql_response(sql_query: str) -> str:
    """
    Clean SQL response from LLM - remove markdown code blocks, extra whitespace, etc.
    """
    # Remove markdown code blocks (```sql ... ``` or ``` ... ```)
    sql_query = re.sub(r'```(?:sql)?\s*\n?(.*?)\n?```', r'\1', sql_query, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove leading/trailing whitespace
    sql_query = sql_query.strip()
    
    # Remove any leading/trailing quotes if present
    sql_query = sql_query.strip('"\'')
    
    return sql_query


# ---------- Prompt construction ----------

def build_prompt(user_request: str, schema_context: str) -> str:
    return textwrap.dedent(f"""
    You are an expert SQL assistant. Your task is to generate a **single** valid, safe, read-only SQLite query.

    USER REQUEST:
    {user_request}

    DATABASE SCHEMA (SQLite):
    {schema_context}

    REQUIREMENTS:
    - Use ONLY the tables and columns shown in the schema.
    - The query MUST be read-only: no INSERT, UPDATE, DELETE, DROP, ALTER, or CREATE.
    - Prefer explicit column names instead of SELECT * when reasonable.
    - If the request is ambiguous, make a reasonable assumption and proceed.
    - Return ONLY the SQL query, with no explanation, no markdown, no backticks.

    Now output the final SQLite query:
    """).strip()


# ---------- Optional: validate SQL via SQLite Explorer MCP ----------

def validate_sql_direct(database: str, sql_query: str) -> dict:
    """
    Validate SQL by running it directly against the database.
    Fallback when MCP server is not available.
    """
    try:
        db_path = get_database_path_from_name(database)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Execute query (read-only, so safe)
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        conn.close()
        
        return {
            "success": True,
            "preview_row_count": len(rows),
            "columns": columns,
            "types": []
        }
    except sqlite3.Error as e:
        return {
            "success": False,
            "error": f"SQLite error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Validation error: {str(e)}"
        }


def validate_sql(database: str, sql_query: str) -> dict:
    """
    Ask SQLite Explorer MCP to run the query in read-only mode.
    We don't care about full results here, just whether it errors.
    Falls back to direct database validation if MCP server is unavailable.
    """
    try:
        result = mcp_call("run_query", {
            "database": database,
            "sql": sql_query
        })
        # You can trim rows if you want, or just keep metadata
        return {
            "success": True,
            "preview_row_count": len(result.get("rows", [])),
            "columns": result.get("columns", []),
            "types": result.get("types", [])
        }
    except RuntimeError as e:
        # MCP server unavailable - fall back to direct validation
        error_msg = str(e)
        if "Failed to connect" in error_msg or "Connection refused" in error_msg:
            logger.warning(f"MCP server unavailable for validation, using direct database access")
            return validate_sql_direct(database, sql_query)
        else:
            return {
                "success": False,
                "error": f"MCP error: {error_msg}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ---------- Public endpoint: NL → SQL ----------

@app.post("/nl_to_sql", response_model=NLToSQLResponse)
def nl_to_sql(req: NLToSQLRequest):
    """
    Convert natural language to SQL query.
    
    Returns:
        NLToSQLResponse with the generated SQL query, schema context, and validation results.
        
    Raises:
        HTTPException: If any step fails (MCP connection, schema retrieval, LLM call, etc.)
    """
    logger.info(f"Received NL-to-SQL request for database: {req.database}")
    logger.info(f"User request: {req.user_request[:100]}...")  # Log first 100 chars
    
    try:
        # 1. Get schema context from SQLite Explorer MCP
        try:
            logger.info(f"Fetching schema for database: {req.database}")
            schema_context = get_schema_context(req.database)
            logger.info(f"Schema retrieved successfully ({len(schema_context)} chars)")
        except RuntimeError as e:
            logger.error(f"MCP server error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to get database schema from MCP server: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error getting schema: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error getting schema: {str(e)}"
            )

        # 2. Build prompt
        try:
            prompt = build_prompt(req.user_request, schema_context)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to build prompt: {str(e)}"
            )

        # 3. Call LLM
        try:
            logger.info("Calling LLM to generate SQL query...")
            sql_query = call_llm(req.provider, req.api_key, prompt).strip()
            logger.info(f"SQL query generated: {sql_query[:100]}...")  # Log first 100 chars
        except ValueError as e:
            logger.error(f"Invalid request: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request: {str(e)}"
            )
        except RuntimeError as e:
            logger.error(f"LLM API error: {str(e)}")
            raise HTTPException(
                status_code=502,
                detail=f"LLM API error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error calling LLM: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error calling LLM: {str(e)}"
            )

        # 4. Optional: validate SQL via SQLite Explorer MCP
        validation = None
        try:
            logger.info("Validating SQL query...")
            validation = validate_sql(req.database, sql_query)
            logger.info(f"Validation result: {validation.get('success', False)}")
        except Exception as e:
            # Validation failure is not critical - log but don't fail the request
            logger.warning(f"SQL validation failed: {str(e)}")
            validation = {
                "success": False,
                "error": f"Validation error: {str(e)}"
            }

        logger.info("NL-to-SQL request completed successfully")
        return NLToSQLResponse(
            sql_query=sql_query,
            schema_context=schema_context,
            validation=validation
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        error_trace = traceback.format_exc()
        logger.error(f"Unexpected error in nl_to_sql endpoint:\n{error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )