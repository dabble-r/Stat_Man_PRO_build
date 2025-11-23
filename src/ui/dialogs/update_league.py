"""
League update dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_league_update_template
from src.ui.dialogs.dialog_handlers import (
    league_update_handler,
    league_launch_handler,
    league_close_handler
)
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QDate
from src.ui.dialogs.update_theme_dialog import UpdateTheme


class UpdateLeagueDialog(BaseDialog):
    """Dialog to update league admin fields, season dates, and theme."""
    
    def __init__(self, league, selected, message, leaderboard, lv_teams, stack, undo, styles, parent=None):
        # Create template
        template = create_league_update_template(
            update_handler=league_update_handler,
            launch_handler=league_launch_handler,
            close_handler=league_close_handler
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
        
        # Store league-specific state
        self.league_name = self.league.isDefaultName()
        self.new_season = None
        self.new_date = None
        self.theme = None
        
        # Set window title
        default = "League"
        self.setWindowTitle(f"Welcome to the {self.league_name if self.league_name else default}!")
        self.setObjectName("Update League")
        
        # Setup date picker handlers and layout
        date_edit = self.get_custom_widget('date_edit')
        date_combo = self.get_custom_widget('date_combo')
        
        # Create vertical layout for date widgets
        if date_combo and date_edit:
            from PySide6.QtWidgets import QVBoxLayout
            date_layout = QVBoxLayout()
            date_layout.addWidget(date_combo)
            date_layout.addWidget(date_edit)
            
            # Add date layout to content layout
            if hasattr(self, 'content_layout'):
                self.content_layout.addLayout(date_layout)
        
        if date_edit:
            date_edit.dateChanged.connect(self._on_change_date)
            date_edit.setEnabled(False)
        
        if date_combo:
            date_combo.activated.connect(self._on_activate_combo)
            date_combo.currentTextChanged.connect(self._on_text_changed)
        
        # Setup radio button toggle handlers
        if 'admin' in self.radio_buttons:
            for radio in self.radio_buttons['admin']:
                if radio.text() == 'Theme':
                    radio.toggled.connect(self._on_toggle_theme)
        
        # Set initial state based on league name
        if self.league_name is True:
            # Only Name option enabled
            if 'admin' in self.radio_buttons:
                for radio in self.radio_buttons['admin']:
                    if radio.text() != "Name":
                        radio.setEnabled(False)
            if date_combo:
                date_combo.setEnabled(False)
            if date_edit:
                date_edit.setEnabled(False)
        else:
            # All options enabled
            if date_combo:
                date_combo.setEnabled(True)
        
        # Set focus
        if 'input' in self.input_fields:
            self.input_fields['input'].setFocus()
    
    def _on_change_date(self, new_date: QDate):
        """Handle date change."""
        day = new_date.day()
        week = new_date.dayOfWeek()
        month = new_date.month()
        year = new_date.year()
        self.new_date = (day, week, month, year)
    
    def _on_activate_combo(self):
        """Handle combo box activation."""
        self._clear_all()
        if 'input' in self.input_fields:
            self.input_fields['input'].setEnabled(False)
        date_edit = self.get_custom_widget('date_edit')
        if date_edit:
            date_edit.setEnabled(True)
    
    def _on_text_changed(self, text):
        """Handle combo box text change."""
        self.new_season = text
    
    def _on_toggle_theme(self, checked):
        """Handle theme radio toggle."""
        if checked:
            if 'input' in self.input_fields:
                self.input_fields['input'].setEnabled(False)
            date_combo = self.get_custom_widget('date_combo')
            if date_combo:
                date_combo.setEnabled(False)
            self._set_theme()
    
    def _set_theme(self):
        """Open theme selection dialog."""
        dialog = UpdateTheme(None, self.message, parent=self)
        dialog.exec()
        if 'input' in self.input_fields:
            self.input_fields['input'].setEnabled(True)
        date_combo = self.get_custom_widget('date_combo')
        if date_combo:
            date_combo.setEnabled(True)
            date_combo.setCurrentIndex(0)
    
    def _clear_all(self):
        """Clear all inputs."""
        if 'input' in self.input_fields:
            self.input_fields['input'].clear()
        if 'admin' in self.radio_buttons:
            for radio in self.radio_buttons['admin']:
                radio.setEnabled(True)
    
    def _get_league_admin(self):
        """Get selected league admin option."""
        date_combo = self.get_custom_widget('date_combo')
        radio = self.get_selected_option('admin')
        
        if date_combo and date_combo.currentIndex() != 0:
            return date_combo.currentText()
        else:
            return radio
    
    def _set_admin_league(self, stat, val):
        """Set league admin field."""
        if 'Season' in stat:
            if self.new_date:
                day, week, month, year = self.new_date
                self.league.set_admin('admin', stat, f"{month}--{day}--{year}", self)
        else:
            self.league.set_admin('admin', stat, val, self)
    
    def _on_submit(self):
        """Handle submit - enable all options after name is set."""
        date_combo = self.get_custom_widget('date_combo')
        if date_combo:
            date_combo.setEnabled(True)
            date_combo.setCurrentIndex(0)
        
        if 'admin' in self.radio_buttons:
            for radio in self.radio_buttons['admin']:
                radio.setEnabled(True)
        
        self.league_name = self.league.admin['Name']
        self.setWindowTitle(f"Welcome to the {self.league_name}!")
