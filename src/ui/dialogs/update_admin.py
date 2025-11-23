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


class UpdateAdminDialog(BaseDialog):
    """Dialog for updating team admin fields (manager, lineup, positions, max roster)."""
    
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        # Create template
        template = create_admin_update_template(
            update_handler=admin_update_handler,
            undo_handler=admin_undo_handler,
            toggle_handler=admin_toggle_handler
        )
        
        # Create context
        context = {
            'league': league,
            'selected': selected,
            'leaderboard': leaderboard,
            'lv_teams': lv_teams,
            'stack': stack,
            'undo': undo,
            'message': message
        }
        
        # Initialize base dialog
        super().__init__(template, context, parent=parent)
        
        # Initially hide input for lineup/positions
        if 'input' in self.input_fields:
            self.input_fields['input'].hide()
