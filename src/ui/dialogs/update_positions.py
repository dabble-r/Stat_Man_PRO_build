"""
Positions update dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_positions_update_template
from src.ui.dialogs.dialog_handlers import (
    positions_update_handler,
    positions_undo_handler
)


class UpdatePositionsDialog(BaseDialog):
    """Dialog for updating player field positions."""
    
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        # Create template
        template = create_positions_update_template(
            update_handler=positions_update_handler,
            undo_handler=positions_undo_handler
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
