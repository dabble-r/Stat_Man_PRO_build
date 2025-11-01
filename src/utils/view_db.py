#!/usr/bin/env python3
"""Quick database viewer"""
import sqlite3
import sys

db_path = "data/database/League.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")
tables = [row[0] for row in cursor.fetchall()]

print(f"📊 Database: {db_path}\n")
print(f"Tables: {', '.join(tables)}\n")

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"✓ {table}: {count} rows")

print("\n" + "="*50)
print("To view a table, run:")
print(f"  python view_db.py <table_name>")
print("="*50)

# If table name provided, show contents
if len(sys.argv) > 1:
    table = sys.argv[1]
    print(f"\n📋 Contents of '{table}':\n")
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Print header
    print(" | ".join(columns))
    print("-" * 80)
    
    # Print rows
    for row in rows:
        print(" | ".join(str(val) if val is not None else "NULL" for val in row))

conn.close()

