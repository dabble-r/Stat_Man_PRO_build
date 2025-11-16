import os
import sys

# --------------------------------------------------

# Silence all print statements unless STATMANG_DEBUG=1 is set
try:
    if os.environ.get("STATMANG_DEBUG", "0") != "1":
        import builtins
        builtins.print = lambda *args, **kwargs: None
except Exception:
    pass

# --------------------------------------------------

from src.ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from src.ui.styles.stylesheets import StyleSheets
from src.utils.clear_db_startup import clear_database_on_startup

# --------------------------------------------------

if __name__ == "__main__":
    # Clear database before starting application
    clear_database_on_startup()
    
    app = QApplication(sys.argv)
    styles = StyleSheets()
    
    app.setStyleSheet(styles.get_monochrome_1_style())

    window = MainWindow(app)

    sys.exit(app.exec())




