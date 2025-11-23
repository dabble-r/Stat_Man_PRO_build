"""
Dialog modules for the application.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.update_offense import UpdateOffenseDialog
from src.ui.dialogs.update_pitching import UpdatePitchingDialog
from src.ui.dialogs.update_admin import UpdateAdminDialog
from src.ui.dialogs.update_team_stats import UpdateTeamStatsDialog
from src.ui.dialogs.update_lineup import UpdateLineupDialog
from src.ui.dialogs.update_positions import UpdatePositionsDialog
from src.ui.dialogs.remove import RemoveDialog
from src.ui.dialogs.update_theme_dialog import UpdateTheme
from src.ui.dialogs.search_dialog import SearchDialog
from src.ui.dialogs.bar_graph_dialog import BarGraphDialog
from src.ui.dialogs.close import CloseDialog
from src.ui.dialogs.update_league import UpdateLeagueDialog

__all__ = [
    'BaseDialog',
    'UpdateOffenseDialog',
    'UpdatePitchingDialog',
    'UpdateAdminDialog',
    'UpdateTeamStatsDialog',
    'UpdateLineupDialog',
    'UpdatePositionsDialog',
    'RemoveDialog',
    'UpdateTheme',
    'SearchDialog',
    'BarGraphDialog',
    'CloseDialog',
    'UpdateLeagueDialog',
]

