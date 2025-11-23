"""
Theme update dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_theme_update_template
from src.ui.dialogs.dialog_handlers import theme_submit_handler


class UpdateTheme(BaseDialog):
    """Dialog for switching application theme."""
    
    def __init__(self, styles, message, parent=None):
        # Create template
        template = create_theme_update_template(
            submit_handler=theme_submit_handler
        )
        
        # Create context
        context = {
            'league': None,
            'selected': None,
            'leaderboard': None,
            'lv_teams': None,
            'stack': None,
            'undo': None,
            'message': message
        }
        
        # Store styles and parent for handler access
        self.styles = styles
        self.parent_widget = parent
        
        # Initialize base dialog
        super().__init__(template, context, parent=parent)
