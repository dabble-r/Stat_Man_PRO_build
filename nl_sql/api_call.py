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
from pathlib import Path
from typing import Optional, Tuple
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
import sqlglot
from sqlglot import expressions as exp
import requests

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.path_resolver import get_database_path

app = FastAPI(title="NL-to-SQL Server", version="1.0.0")

# Get database path
DB_PATH = get_database_path()

# MCP server URL
MCP_SERVER_URL = "http://localhost:8001"

# Default model
DEFAULT_MODEL = "gpt-4o-mini"


class QueryRequest(BaseModel):
    """Request model for NL query."""
    question: str
    api_key: Optional[str] = None  # Optional, prefer Authorization header


def get_api_key_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def get_api_key(
    request: QueryRequest,
    authorization: Optional[str] = Depends(get_api_key_from_header)
) -> str:
    """
    Get API key from request (header preferred, body fallback, then environment).
    
    Args:
        request: Query request object
        authorization: Authorization header value
        
    Returns:
        str: API key
        
    Raises:
        HTTPException: If no API key found
    """
    # Priority: Header > Request body > Environment variable
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


async def get_database_schema() -> str:
    """
    Get database schema from MCP server.
    
    Returns:
        str: Database schema, or fallback schema if database is empty
    """
    try:
        response = requests.get(f"{MCP_SERVER_URL}/schema", timeout=5)
        if response.status_code == 200:
            schema = response.json().get("schema", "")
            
            # If schema is empty, provide fallback schema based on expected structure
            if not schema or not schema.strip():
                return get_fallback_schema()
            
            return schema
        else:
            # MCP server unavailable, use fallback
            return get_fallback_schema()
    except Exception:
        # MCP server unavailable, use fallback
        return get_fallback_schema()


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


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "NL-to-SQL Server"}


@app.post("/mcp/ask")
async def ask_nl_query(
    request: QueryRequest,
    api_key: str = Depends(get_api_key)
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
    api_key: str = Depends(get_api_key)
):
    """
    Alias for /mcp/ask endpoint.
    """
    return await ask_nl_query(request, api_key)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
