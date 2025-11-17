import sys

# --------------------------------------------------

# --------------------------------------------------

from src.ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from src.ui.styles.stylesheets import StyleSheets
from src.utils.clear_db_startup import clear_database_on_startup
from src.utils.print_filter import mute_print

# --------------------------------------------------

if __name__ == "__main__":
    # mute print statements unless STATMANG_DEBUG=1 is set
    mute_print() 

    # Clear database before starting application
    clear_database_on_startup()
    
    app = QApplication(sys.argv)
    styles = StyleSheets()
    
    app.setStyleSheet(styles.get_monochrome_1_style())

    window = MainWindow(app)

    sys.exit(app.exec())




