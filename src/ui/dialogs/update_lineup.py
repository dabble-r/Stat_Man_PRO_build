"""
Lineup update dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_lineup_update_template
from src.ui.dialogs.dialog_handlers import (
    lineup_update_handler,
    lineup_undo_handler,
    lineup_toggle_handler
)
from src.ui.context.app_context import AppContext


class UpdateLineupDialog(BaseDialog):
    """Dialog for updating team batting lineup."""

    def __init__(self, context: AppContext, parent=None):
        template = create_lineup_update_template(
            update_handler=lineup_update_handler,
            undo_handler=lineup_undo_handler,
            toggle_handler=lineup_toggle_handler
        )
        super().__init__(template, context.to_dict(), parent=parent)
        self.context = context
