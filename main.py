import os
import sys
from pathlib import Path
import sqlite3

# Silence all print statements unless STATMANG_DEBUG=1 is set
try:
    if os.environ.get("STATMANG_DEBUG", "0") != "1":
        import builtins
        builtins.print = lambda *args, **kwargs: None
except Exception:
    pass

from src.ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from src.utils.img_repo import CreateDir
from src.ui.styles.stylesheets import StyleSheets
from src.utils.path_resolver import get_database_path

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

if __name__ == "__main__":
    # Clear database before starting application
    clear_database_on_startup()
    
    app = QApplication(sys.argv)
    styles = StyleSheets()
    app.setStyleSheet(styles.get_monochrome_1_style())

    window = MainWindow(app)

    sys.exit(app.exec())




