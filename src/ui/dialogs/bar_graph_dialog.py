"""
Bar graph team selection dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_bar_graph_template


class BarGraphDialog(BaseDialog):
    """Dialog for selecting teams to display in bar graph."""
    
    def __init__(self, league, selected, message, teams, parent):
        # Lazy import to avoid circular dependency
        from src.ui.dialogs.dialog_handlers import bar_graph_submit_handler
        
        # Get team names from league
        team_names = league.get_all_team_names() if league else []
        
        # Create template
        template = create_bar_graph_template(
            submit_handler=bar_graph_submit_handler
        )
        
        # Update options with actual team names
        if 'selection' in template:
            template['selection']['options'] = team_names
        
        # Create context
        context = {
            'league': league,
            'selected': selected,
            'leaderboard': None,
            'lv_teams': None,
            'stack': None,
            'undo': None,
            'message': message
        }
        
        # Initialize base dialog
        super().__init__(template, context, parent=parent)
        
        # Store parent and teams list for checkbox handler
        self.parent_widget = parent
        self.teams_selected = teams
        self.max_check = 6
        
        # Setup checkbox change handler
        if 'selection' in self.checkboxes:
            for checkbox in self.checkboxes['selection']:
                checkbox.stateChanged.connect(self._check_on_change)
    
    def _check_on_change(self):
        """Handle checkbox state change."""
        for checkbox in self.checkboxes.get('selection', []):
            team = checkbox.text()
            if checkbox.isChecked():
                if team not in self.teams_selected:
                    if len(self.teams_selected) < self.max_check:
                        self.teams_selected.append(team)
                    else:
                        self.show_validation_error("Limit six teams per graph.")
                        checkbox.setChecked(False)
                if team not in self.parent_widget.teams_selected:
                    if len(self.parent_widget.teams_selected) < self.max_check:
                        self.parent_widget.teams_selected.append(team)
            else:
                if team in self.teams_selected:
                    self.teams_selected.remove(team)
                if team in self.parent_widget.teams_selected:
                    self.parent_widget.teams_selected.remove(team)
