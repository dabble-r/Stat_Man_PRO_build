from PySide6.QtWidgets import QMessageBox, QDialog
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFontMetrics

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt



class Message_1(QDialog):
  def __init__(self, styles, parent=None):
    """Simple message box wrapper for OK-only notifications with autosizing."""
    self.parent = parent
    self.box = QMessageBox(parent=self.parent)
    self.styles = styles
    self.box.setWindowTitle('Update Message')
    self.box.setStandardButtons(QMessageBox.Ok)
    #self.box.setStyleSheet(self.styles.modern_styles)
    self.choice = None

  def set_box_text(self, text):
    """Set message text on the internal QMessageBox."""
    self.box.setText(text)

  def show_message(self, text):
    """Show message modally after adjusting box size to content."""
    self.set_box_text(text)
    self._resize_to_fit_text(text)

    # show not functional - non-modal
    #self.box.show()

    # message exec - modal
    self.box.exec()
  
  def _resize_to_fit_text(self, text):
        """Compute and set a minimum dialog size based on text metrics."""
        # Use font metrics to calculate text size
        font_metrics = QFontMetrics(self.box.font())
        text_width = font_metrics.horizontalAdvance(text)
        text_height = font_metrics.height()

        # Add padding and set minimum size
        padding = 100  # Adjust as needed
        min_width = max(250, text_width + padding)
        min_height = 150  # You can also adjust based on line count

        self.box.setMinimumSize(min_width, min_height)

   
    
    


class Message(QDialog):
    def __init__(self, styles=None, parent=None):
        """Flexible message dialog returning 'ok'/'no'/'cancel' per user choice."""
        super().__init__(parent)
        self.styles = styles
        self.setWindowTitle("Update Message")
        self.choice = None

        # Layout
        self.layout = QVBoxLayout(self)

        # Message label
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)

        # Buttons: OK, No, Cancel
        self.buttons = QDialogButtonBox(self)
        self.buttons.setStandardButtons(
            QDialogButtonBox.Ok | QDialogButtonBox.No | QDialogButtonBox.Cancel
        )
        self.layout.addWidget(self.buttons)

        # Connect button clicks
        self.buttons.accepted.connect(self._handle_ok)      # OK
        self.buttons.rejected.connect(self._handle_cancel)  # Cancel
        self.buttons.button(QDialogButtonBox.No).clicked.connect(self._handle_no)


    def set_box_text(self, text: str):
        """Set the message text and resize the dialog accordingly."""
        self.label.setText(text)
        self._resize_to_fit_text(text)

    def show_message(self, text: str) -> str:
        """Show the dialog and return the clicked button value."""
        self.set_box_text(text)
        self.exec()
        return self.choice

    def _resize_to_fit_text(self, text: str):
        """Resize dialog width dynamically based on text length."""
        font_metrics = QFontMetrics(self.label.font())
        text_width = font_metrics.horizontalAdvance(text)
        padding = 100
        min_width = max(250, text_width + padding)
        min_height = 150
        self.setMinimumSize(min_width, min_height)

    # Handlers for button clicks
    def _handle_ok(self):
        self.choice = "ok"
        self.accept()

    def _handle_no(self):
        self.choice = "no"
        self.accept()

    def _handle_cancel(self):
        self.choice = "cancel"
        self.reject()
    