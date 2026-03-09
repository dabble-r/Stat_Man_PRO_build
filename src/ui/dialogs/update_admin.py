"""
Team admin/management update dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_admin_update_template
from src.ui.dialogs.dialog_handlers import (
    admin_update_handler,
    admin_undo_handler,
    admin_toggle_handler
)
from src.ui.context.app_context import AppContext


class UpdateAdminDialog(BaseDialog):
    """Dialog for updating team admin fields (manager, lineup, positions, max roster)."""

    def __init__(self, context: AppContext, parent=None):
        template = create_admin_update_template(
            update_handler=admin_update_handler,
            undo_handler=admin_undo_handler,
            toggle_handler=admin_toggle_handler
        )
        super().__init__(template, context.to_dict(), parent=parent)
        self.context = context
        
        # Initially hide input for lineup/positions
        if 'input' in self.input_fields:
            self.input_fields['input'].hide()
