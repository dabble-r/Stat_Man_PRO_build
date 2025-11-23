"""
Close confirmation dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.dialog_templates import ConfirmationTemplate
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QCloseEvent


class CloseDialog(BaseDialog):
    """Simple confirmation dialog to guard against accidental app exit."""
    
    def __init__(self):
        # Create template
        template = ConfirmationTemplate.create_template(
            title="Confirm Exit",
            options=["Yes", "No"],
            default_option="No",
            submit_handler=self._handle_close,
            submit_label="Confirm"
        )
        
        # Create context
        context = {
            'league': None,
            'selected': None,
            'leaderboard': None,
            'lv_teams': None,
            'stack': None,
            'undo': None,
            'message': None
        }
        
        # Initialize base dialog
        super().__init__(template, context, parent=None)
        
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | self.WindowType.Dialog | 
                           self.WindowType.WindowTitleHint | 
                           self.WindowType.CustomizeWindowHint)
    
    def _handle_close(self, dialog):
        """Handle close confirmation."""
        selection = dialog.get_selected_option('confirmation')
        if selection == "Yes":
            dialog.accept()
        else:
            dialog.reject()
    
    def close_message(self, event: QCloseEvent):
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
