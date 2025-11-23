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


class UpdateLineupDialog(BaseDialog):
    """Dialog for updating team batting lineup."""
    
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        # Create template
        template = create_lineup_update_template(
            update_handler=lineup_update_handler,
            undo_handler=lineup_undo_handler,
            toggle_handler=lineup_toggle_handler
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
