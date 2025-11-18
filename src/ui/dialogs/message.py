from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt, QTimer


class Message(QDialog):
    def __init__(self, parent=None, timeout_ms=None):
        """Flexible message dialog returning 'ok'/'no'/'cancel' per user choice."""
        super().__init__(parent)
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

    def set_timer(self, timeout_ms: int): 
        self.timer = QTimer(self)
        self.timer.setSingleShot(True) # Timer fires only once
        self.timer.timeout.connect(self.reject) # Close dialog (as rejected) when timer expires
        self.timer.start(timeout_ms) # Start the timer with the specified timeout

    def set_buttons(self, flag: bool):
        if flag:
            self.buttons.setVisible(True)
        else:
            self.buttons.setVisible(False)

    def set_box_text(self, text: str):
        """Set the message text and resize the dialog accordingly."""
        self.label.setText(text)
        self._resize_to_fit_text(text)

    def show_message(self, text: str, btns_flag: bool = True, timeout_ms: int = 2000) -> str:
        """Show the dialog and return the clicked button value."""
        self.set_box_text(text)
        if not btns_flag:
            self.set_buttons(False)
            self.set_timer(timeout_ms)
        else:
            self.set_buttons(True)
        
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
    