"""
MCP Server for Database Operations (Port 8001)

This server handles:
- Database schema extraction
- SQL query execution (read-only)
- Run plot (execute LLM-generated Python code, return PNG)
- Health checks

Does NOT require API key.
"""

import json
import subprocess
import sys
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.path_resolver import get_database_path
from src.utils.nl_plot_log import get_nl_plot_logger

app = FastAPI(title="MCP Server", version="1.0.0")

# Get database path - ALWAYS prefer project root database
# When running as subprocess, working directory may differ, so always use project root
_project_db_path = project_root / "data" / "database" / "League.db"
_initial_db_path = get_database_path()

# Always prefer project root database if it exists (this is the correct database)
# Only use initial path if project root database doesn't exist
if _project_db_path.exists():
    DB_PATH = _project_db_path
elif _initial_db_path.exists():
    # Fallback: use initial path if project root doesn't exist
    # But log a warning as this may be the wrong database
    import logging
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger(__name__)
    logger.warning(f"Using database from get_database_path(): {_initial_db_path}")
    logger.warning(f"Project root database not found at: {_project_db_path}")
    DB_PATH = _initial_db_path
else:
    # Neither exists, use project root path (will error clearly)
    DB_PATH = _project_db_path


def get_schema(db_path: Path) -> str:
    """
    Extract database schema for LLM consumption.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        str: Formatted schema string
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    schema_parts = []
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Format: table_name(column1 type, column2 type, ...)
        col_defs = []
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            col_defs.append(f"{col_name} {col_type}")
        
        schema_parts.append(f"{table_name}({', '.join(col_defs)})")
    
    conn.close()
    
    return "\n".join(schema_parts)


# Columns for which we return distinct values so NL-to-SQL uses actual DB values (e.g. "second base" not "2B")
VALUE_HINT_COLUMNS = ["positions"]


def get_distinct_values(db_path: Path, column: str, max_values: int = 200) -> List[str]:
    """
    Get distinct non-empty values for a column from tables that have it.
    Used so NL-to-SQL prompts can tell the LLM to use exact DB values (e.g. "second base" not "2B").
    """
    if not column or column not in VALUE_HINT_COLUMNS:
        return []
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        seen: set = set()
        result: List[str] = []
        for table in tables:
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                cols = [row[1] for row in cursor.fetchall()]
                if column not in cols:
                    continue
                cursor.execute(f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL AND "{column}" != ""')
                for (val,) in cursor.fetchall():
                    val = (val or "").strip()
                    if not val:
                        continue
                    # Column may store comma-separated values (e.g. "second base,outfield")
                    for part in [p.strip() for p in val.split(",") if p.strip()]:
                        if part not in seen:
                            seen.add(part)
                            result.append(part)
                            if len(result) >= max_values:
                                break
                    if len(result) >= max_values:
                        break
            except sqlite3.Error:
                continue
            if len(result) >= max_values:
                break
        conn.close()
        return sorted(result)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return []


@app.get("/distinct_values")
async def get_distinct_values_endpoint(column: str = ""):
    """
    Get distinct values for a column (e.g. positions) so NL-to-SQL uses exact DB values.
    Query params: column (e.g. "positions").
    """
    try:
        if not column.strip():
            return {"values": [], "column": "", "message": "Query param 'column' required (e.g. positions)."}
        values = get_distinct_values(DB_PATH, column.strip())
        return {"values": values, "column": column.strip(), "database": str(DB_PATH)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting distinct values: {str(e)}")


class RunPlotRequest(BaseModel):
    """Request body for running plot code."""
    code: str
    data: List[Dict[str, Any]]


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MCP Server"}


@app.get("/schema")
async def get_schema_endpoint():
    """
    Get database schema.
    
    Returns:
        JSON with schema string
    """
    try:
        schema = get_schema(DB_PATH)
        
        # Check if schema is empty (only system tables)
        if not schema or not schema.strip() or schema.strip() == "sqlite_sequence(sqlite_sequence)":
            # Database is empty - return empty schema (FastAPI will use fallback)
            return {"schema": "", "database": str(DB_PATH), "warning": "Database exists but contains no data tables. Using fallback schema."}
        
        return {"schema": schema, "database": str(DB_PATH)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Database not found: {str(e)}")
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting schema: {str(e)}")


@app.post("/execute")
async def execute_query(query: dict):
    """
    Execute a read-only SQL query.
    
    Args:
        query: Dict with 'sql' key containing SQL query
        
    Returns:
        JSON with query results
    """
    sql = query.get("sql", "")
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query required")
    
    # Validate SQL - only SELECT allowed
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed"
        )
    
    # Check for dangerous operations
    dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Dangerous operation detected: {keyword}"
            )
    
    try:
        # Verify database path and connection
        if not DB_PATH.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Database not found at: {DB_PATH}. Current working directory: {Path.cwd()}"
            )
        
        # Connect to database
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        cursor = conn.cursor()
        
        # Verify tables exist before executing
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        available_tables = [row[0] for row in cursor.fetchall()]
        
        # Extract table name from SQL query (simple check)
        sql_lower = sql.lower().strip()
        if sql_lower.startswith('select'):
            # Try to find table name in query
            import re
            # Look for FROM clause
            from_match = re.search(r'\bfrom\s+(\w+)', sql_lower)
            if from_match:
                requested_table = from_match.group(1)
                if requested_table not in available_tables:
                    conn.close()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Table '{requested_table}' not found. Available tables: {available_tables}. Database path: {DB_PATH}"
                    )
        
        # Execute query
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # Convert rows to list of dicts
        results = [dict(row) for row in rows]
        
        conn.close()
        
        return {
            "success": True,
            "row_count": len(results),
            "results": results
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=f"SQL error: {str(e)}. Database path: {DB_PATH}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing query: {str(e)}. Database path: {DB_PATH}")


# Timeout in seconds for running plot code
RUN_PLOT_TIMEOUT = 30  # Strategy 1: consistent long timeout for MCP run_plot


@app.post("/run_plot")
async def run_plot(request: RunPlotRequest):
    """
    Run LLM-generated Python plot code with the given data.

    Request: code (str), data (list of dict - rows for DataFrame).
    Returns: JSON with png_base64 (str) on success, or error (str) on failure.
    """
    code = (request.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    if not request.data:
        raise HTTPException(status_code=400, detail="data is required")

    # Log the Python code run by MCP (verbose nl_plot log)
    try:
        nl_log = get_nl_plot_logger()
        nl_log.info("MCP run_plot: executing code (length=%d, data_rows=%d)", len(code), len(request.data or []))
        nl_log.info("MCP run_plot code:\n--- BEGIN MCP EXEC CODE ---\n%s\n--- END MCP EXEC CODE ---", code)
    except Exception:
        pass

    payload = {"code": code, "data": request.data}
    try:
        input_bytes = json.dumps(payload).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {e}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "nl_sql.run_plot_worker"],
            input=input_bytes,
            capture_output=True,
            timeout=RUN_PLOT_TIMEOUT,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail=f"Plot execution timed out after {RUN_PLOT_TIMEOUT}s"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run plot worker: {e}"
        )

    stderr_text = (result.stderr or b"").decode("utf-8", errors="replace").strip()
    if result.returncode != 0:
        msg = stderr_text or f"Worker exited with code {result.returncode}"
        if "ERROR:" in msg:
            msg = msg.split("ERROR:")[-1].strip()
        raise HTTPException(status_code=400, detail=msg)

    stdout_text = (result.stdout or b"").decode("utf-8", errors="replace").strip()
    if not stdout_text:
        raise HTTPException(status_code=502, detail="Worker produced no output")

    return {"png_base64": stdout_text}


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
