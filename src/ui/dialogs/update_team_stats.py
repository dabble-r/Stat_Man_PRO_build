"""
Team stats update dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_team_stats_update_template
from src.ui.dialogs.dialog_handlers import (
    team_stats_update_handler,
    team_stats_undo_handler,
    team_stats_view_handler,
    create_team_stats_enablement_check
)


class UpdateTeamStatsDialog(BaseDialog):
    """Dialog for updating team statistics."""
    
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, styles, parent=None):
        # Create template
        template = create_team_stats_update_template(
            update_handler=team_stats_update_handler,
            undo_handler=team_stats_undo_handler,
            view_handler=team_stats_view_handler,
            enablement_check=None  # Will be set after initialization
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
        
        # Set enablement check and apply to radio buttons
        enablement_check = create_team_stats_enablement_check(self)
        if 'stats' in self.radio_buttons:
            for i, radio in enumerate(self.radio_buttons['stats']):
                option = radio.text()
                enabled = enablement_check(option, self)
                radio.setEnabled(enabled)
