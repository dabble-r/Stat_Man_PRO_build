from src.utils.path_resolver import get_database_path
import sqlite3

def clear_database_on_startup():
    """Clear all data from database on startup - database doesn't persist between sessions"""
    # Use path resolver to ensure it works in both dev and bundled mode
    db_path = get_database_path()
    
    if not db_path.exists():
        print("No database to clear on startup.")
        return
    
    try:
        print(f"Clearing database on startup: {db_path}")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        # Drop all tables
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            print(f"  Dropped table: {table_name}")
        
        conn.commit()
        conn.close()
        print("Database cleared successfully.")
        
    except Exception as e:
        print(f"Error clearing database on startup: {e}")