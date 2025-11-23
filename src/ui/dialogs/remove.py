"""
Remove item dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_remove_template
from src.ui.dialogs.dialog_handlers import remove_submit_handler


class RemoveDialog(BaseDialog):
    """Dialog for removing teams or players from league or current view."""
    
    def __init__(self, league, selected, leaderboard, lv_teams, lv_players, parent=None):
        # Create template
        template = create_remove_template(
            submit_handler=remove_submit_handler
        )
        
        # Create context
        context = {
            'league': league,
            'selected': selected,
            'leaderboard': leaderboard,
            'lv_teams': lv_teams,
            'lv_players': lv_players,
            'stack': None,  # Not used for remove
            'undo': None,   # Not used for remove
            'message': None  # Not used for remove
        }
        
        # Initialize base dialog
        super().__init__(template, context, parent=parent)
        
        # Store lv_players for remove operations
        self.lv_players = lv_players
