"""
Positions update dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_positions_update_template
from src.ui.dialogs.dialog_handlers import (
    positions_update_handler,
    positions_undo_handler
)
from src.ui.context.app_context import AppContext


class UpdatePositionsDialog(BaseDialog):
    """Dialog for updating player field positions."""

    def __init__(self, context: AppContext, parent=None):
        template = create_positions_update_template(
            update_handler=positions_update_handler,
            undo_handler=positions_undo_handler
        )
        super().__init__(template, context.to_dict(), parent=parent)
        self.context = context
