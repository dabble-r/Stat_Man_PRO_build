import sys
import os
from pathlib import Path

# --------------------------------------------------

# --------------------------------------------------

from src.ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui.styles.stylesheets import StyleSheets
from src.utils.clear_db_startup import clear_database_on_startup
from src.utils.print_filter import mute_print
from src.utils.path_resolver import get_app_base_path

# --------------------------------------------------

if __name__ == "__main__":
    # mute print statements unless STATMANG_DEBUG=1 is set
    mute_print() 

    # Clear database before starting application
    clear_database_on_startup()
    
    app = QApplication(sys.argv)
    styles = StyleSheets()
    
    app.setStyleSheet(styles.get_monochrome_1_style())

    # Set application icon (works in both development and packaged modes)
    icon_path = Path(get_app_base_path()) / 'assets' / 'icons' / 'pbl_logo_ICO.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    # If icon not found, continue without icon (no error)

    window = MainWindow(app)

    sys.exit(app.exec())




