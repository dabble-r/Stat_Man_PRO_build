#!/usr/bin/env python3
"""
SQLite Explorer MCP Server

This server implements the Model Context Protocol (MCP) for SQLite database exploration.
It provides JSON-RPC 2.0 endpoints for:
- list_tables: Get all tables in a database
- get_table_schema: Get schema information for a specific table
- run_query: Execute a SQL query and return results

Usage:
    python mcp_server.py
    Or with uvicorn:
    uvicorn mcp_server:app --host 0.0.0.0 --port 8001
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SQLite Explorer MCP Server")

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


# ---------- JSON-RPC 2.0 Models ----------

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any
    method: str
    params: Dict[str, Any]


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Any
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


# ---------- Database Path Resolution ----------

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
        Path(f"data/database/{database}.db"),
        Path(f"../data/database/{database}.db"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    
    raise ValueError(f"Could not find database file for '{database}'")


# ---------- MCP Methods ----------

def list_tables(database: str) -> Dict[str, Any]:
    """List all tables in the database."""
    try:
        db_path = get_database_path_from_name(database)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [{"name": row[0]} for row in cursor.fetchall()]
        
        conn.close()
        
        logger.info(f"Listed {len(tables)} tables from database: {database}")
        return {"tables": tables}
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        raise ValueError(f"Failed to list tables: {str(e)}")


def get_table_schema(database: str, table: str) -> Dict[str, Any]:
    """Get schema information for a specific table."""
    try:
        db_path = get_database_path_from_name(database)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get table schema using PRAGMA
        cursor.execute(f"PRAGMA table_info({table})")
        rows = cursor.fetchall()
        
        columns = []
        for row in rows:
            col_id, col_name, col_type, not_null, default_val, pk = row
            columns.append({
                "name": col_name,
                "type": col_type or "TEXT",  # Default to TEXT if no type specified
                "not_null": bool(not_null),
                "default": default_val,
                "primary_key": bool(pk)
            })
        
        conn.close()
        
        logger.info(f"Retrieved schema for table '{table}' in database '{database}': {len(columns)} columns")
        return {"columns": columns}
    except Exception as e:
        logger.error(f"Error getting table schema: {str(e)}")
        raise ValueError(f"Failed to get schema for table '{table}': {str(e)}")


def run_query(database: str, sql: str) -> Dict[str, Any]:
    """Execute a SQL query and return results."""
    try:
        db_path = get_database_path_from_name(database)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Execute query
        cursor.execute(sql)
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Get all rows
        rows = cursor.fetchall()
        
        # Get column types
        types = []
        if rows and columns:
            # Infer types from first row
            for i, val in enumerate(rows[0]):
                if val is None:
                    types.append("NULL")
                elif isinstance(val, int):
                    types.append("INTEGER")
                elif isinstance(val, float):
                    types.append("REAL")
                else:
                    types.append("TEXT")
        else:
            types = ["TEXT"] * len(columns)
        
        conn.close()
        
        logger.info(f"Executed query on database '{database}': {len(rows)} rows returned")
        return {
            "columns": columns,
            "types": types,
            "rows": [list(row) for row in rows]  # Convert tuples to lists for JSON serialization
        }
    except sqlite3.Error as e:
        logger.error(f"SQLite error executing query: {str(e)}")
        raise ValueError(f"SQL error: {str(e)}")
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise ValueError(f"Failed to execute query: {str(e)}")


# ---------- JSON-RPC 2.0 Handler ----------

def handle_jsonrpc_request(request: JSONRPCRequest) -> JSONRPCResponse:
    """Handle a JSON-RPC 2.0 request."""
    method_handlers = {
        "list_tables": list_tables,
        "get_table_schema": get_table_schema,
        "run_query": run_query,
    }
    
    if request.method not in method_handlers:
        return JSONRPCResponse(
            id=request.id,
            error=JSONRPCError(
                code=-32601,
                message=f"Method not found: {request.method}"
            )
        )
    
    try:
        handler = method_handlers[request.method]
        result = handler(**request.params)
        return JSONRPCResponse(
            id=request.id,
            result=result
        )
    except ValueError as e:
        # User/application error
        return JSONRPCResponse(
            id=request.id,
            error=JSONRPCError(
                code=-32000,
                message=str(e)
            )
        )
    except Exception as e:
        # Internal server error
        logger.error(f"Internal error handling {request.method}: {str(e)}")
        return JSONRPCResponse(
            id=request.id,
            error=JSONRPCError(
                code=-32603,
                message=f"Internal error: {str(e)}"
            )
        )


# ---------- FastAPI Endpoints ----------

@app.post("/mcp", response_model=JSONRPCResponse)
async def mcp_endpoint(request: JSONRPCRequest):
    """Handle JSON-RPC 2.0 MCP requests."""
    logger.info(f"Received MCP request: {request.method} with params: {request.params}")
    response = handle_jsonrpc_request(request)
    if response.error:
        logger.warning(f"MCP request failed: {response.error.message}")
    return response


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "SQLite Explorer MCP Server",
        "version": "1.0.0",
        "status": "running",
        "endpoint": "/mcp"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting SQLite Explorer MCP Server")
    print("=" * 60)
    print(f"Server will run at: http://localhost:8001")
    print(f"MCP endpoint: http://localhost:8001/mcp")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
