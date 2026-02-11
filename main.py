import sys
import os
from pathlib import Path

# --------------------------------------------------
# server_fail_4 Solution A: when frozen, load uvicorn early so in-process server threads can import it
if getattr(sys, 'frozen', False):
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        pass
# --------------------------------------------------

from src.ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui.styles.stylesheets import StyleSheets
from src.utils.clear_db_startup import clear_database_on_startup
from src.utils.ensure_nl_db import ensure_nl_database_schema
from src.utils.print_filter import mute_print
from src.utils.path_resolver import get_resource_path
from src.utils.nl_sql_server import NLServerManager
from src.utils.api_key_manager import APIKeyManager

# --------------------------------------------------


def ensure_ports_free():
    """Ensure ports 8000 and 8001 are free on program startup."""
    print("[Main] Checking and freeing ports 8000 and 8001...")
    
    # Create a temporary server manager just for port checking
    # We don't need to keep it, just use its port checking method
    temp_manager = NLServerManager()
    
    # Check and free both ports
    port_8000_free = temp_manager._check_and_free_port(8000)
    port_8001_free = temp_manager._check_and_free_port(8001)
    
    if port_8000_free and port_8001_free:
        print("[Main] Ports 8000 and 8001 are free and ready")
    else:
        print("[Main] Warning: Some ports may still be in use")
    
    return port_8000_free and port_8001_free


if __name__ == "__main__":
    # mute print statements unless STATMANG_DEBUG=1 is set
    mute_print() 

    # Clear database before starting application
    clear_database_on_startup()

    # When frozen, ensure NL local-SQL DB has schema (league/team/player/pitcher)
    ensure_nl_database_schema()

    # Ensure ports 8000 and 8001 are free
    ensure_ports_free()
    
    app = QApplication(sys.argv)
    styles = StyleSheets()
    
    app.setStyleSheet(styles.get_monochrome_1_style())

    # Set application icon (works in both development and packaged modes)
    # Use get_resource_path to handle PyInstaller's _MEIPASS extraction
    icon_path_str = get_resource_path('assets/icons/pbl_logo_ICO.ico')
    icon_path = Path(icon_path_str)
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    # If icon not found, continue without icon (no error)

    window = MainWindow(app)

    # Clear saved API key when program exits (session-only persistence)
    def clear_api_key_on_exit():
        APIKeyManager().clear_api_key()
    app.aboutToQuit.connect(clear_api_key_on_exit)

    sys.exit(app.exec())




