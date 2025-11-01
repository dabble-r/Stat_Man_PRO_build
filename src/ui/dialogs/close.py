from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QCloseEvent
import sys

class CloseDialog(QDialog):
    def __init__(self):
        """Simple confirmation dialog to guard against accidental app exit."""
        super().__init__()
        self.setWindowTitle("Confirm Exit")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint)

    def close_message(self, event=QCloseEvent):
        """Ask user to confirm closing; accept or ignore the provided close event."""
        reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Are you sure you want to quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
            
        elif reply == QMessageBox.StandardButton.No:
            event.ignore()
            #self.show()
            #self.show()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = CloseDialog()
    
    if dialog.exec() == QDialog.Accepted:
        print("User confirmed exit.")
    else:
        
        print("User canceled.")
    sys.exit()