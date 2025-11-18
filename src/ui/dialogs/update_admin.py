from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt
from src.ui.styles.stylesheets import StyleSheets
from src.ui.logic.dialogs.update_admin_logic import (
    normalize_stat_name_for_stack,
    set_new_stat_team,
    update_stats,
    update_lineup_handler as update_lineup_handler_logic,
    update_positions_handler as update_positions_handler_logic,
)

# --------------------------------------------------

class UpdateAdminDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        """Management dialog to edit team manager, lineup, positions, and roster size."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.message = message
        self.setWindowTitle("Update Management")
        self.resize(400, 300)
        self.styles = StyleSheets()
        #self.setStyleSheet(self.styles.main_styles)
        
        # Widgets
        self.input_label = QLabel("Enter value:")
        self.input_label.setAlignment(Qt.AlignCenter)
        self.input = QLineEdit()
        self.input.setAlignment(Qt.AlignCenter)

        # ----- Submit Button ----- #
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.update_stats_handler)

        # ----- Undo Button ----- #
        self.undo_button = QPushButton("Undo")
        self.undo_button.setFixedWidth(100)
        self.undo_button.clicked.connect(self.undo_stat)

        # -------- Buttons Layout ----- # 
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.buttons_layout.addWidget(self.undo_button, alignment=Qt.AlignCenter)

        self.form_layout = QVBoxLayout()
        self.form_layout.addWidget(self.input_label)
        self.form_layout.addWidget(self.input)

        self.form_widget = QWidget()
        self.form_widget.setLayout(self.form_layout)
        self.form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                            # ----------------------------------------------------------------------------------------------------- # 

        # Right side: Radio Buttons in a group
        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []

        options = ["default"]

        options = ["manager", "lineup", "positions", "max roster"]

        radio_buttons_layout = QVBoxLayout()
        radio_buttons_layout.setAlignment(Qt.AlignTop)

        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            radio.toggled.connect(self.render_input_form)
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            radio_buttons_layout.addWidget(radio)

        # Container widget for the radio buttons (optional)
        radio_buttons_widget = QWidget()
        radio_buttons_widget.setLayout(radio_buttons_layout)

                                # ---------------------------------------------------------------------------------------------------------------------#

        # Horizontal layout: form on the left, radios on the right
        self.content_layout = QHBoxLayout()
        self.content_layout.addStretch()
        self.content_layout.addWidget(self.form_widget)
        # hide on render
        self.form_widget.hide()
        self.content_layout.addSpacing(40)  # spacing between form and radios
        self.content_layout.addWidget(radio_buttons_widget)
        self.content_layout.addStretch()

         # ----- Main Layout ----- #
        self.main_layout = QVBoxLayout()
        self.main_layout.addStretch()
        self.main_layout.addLayout(self.content_layout)
        self.main_layout.addSpacing(20)
        self.main_layout.addLayout(self.buttons_layout)

        self.setLayout(self.main_layout)

    def get_team_stat(self):
        """Return selected admin stat label from radio buttons."""
        # radio button selection 
        selection = self.radio_group.checkedButton().text()
        return selection
    
    def render_input_form(self):
        """Show/hide input field and validators based on selected admin option."""
        text = self.radio_group.checkedButton().text()
        if text == "lineup" or text == "positions":
            self.form_widget.hide()
        elif text == "max roster":
            rost_int = QIntValidator(1, 50)
            self.form_widget.show()
            self.input.setValidator(rost_int)
        else:
            self.form_widget.show()
        

    def _create_lineup_handler_wrapper(self):
        """Create a wrapper function that captures dialog instance data for the lineup handler."""
        def wrapper(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=None):
            """Wrapper that calls the logic function with dialog's instance data."""
            update_lineup_handler_logic(
                league_instance, 
                selected, 
                leaderboard_instance, 
                lv_teams_instance, 
                stack_instance, 
                undo_instance, 
                message_instance, 
                parent=parent
            )
        return wrapper

    def _create_positions_handler_wrapper(self):
        """Create a wrapper function that captures dialog instance data for the positions handler."""
        def wrapper(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=None):
            """Wrapper that calls the logic function with dialog's instance data."""
            update_positions_handler_logic(
                league_instance, 
                selected, 
                leaderboard_instance, 
                lv_teams_instance, 
                stack_instance, 
                undo_instance, 
                message_instance, 
                parent=parent
            )
        return wrapper


    def update_stats_handler(self):
        # Create wrapper for lineup handler that matches the expected signature
        lineup_handler_wrapper = self._create_lineup_handler_wrapper()
        positions_handler_wrapper = self._create_positions_handler_wrapper()

        update_stats(
            self.selected, 
            self.get_team_stat, 
            lineup_handler_wrapper, 
            positions_handler_wrapper, 
            self.input, 
            self.message, 
            self.league, 
            self.stack, 
            self.undo, 
            self.leaderboard, 
            self.lv_teams, 
            set_new_stat_team, 
            normalize_stat_name_for_stack, 
            parent=self
        )

    
    def undo_stat(self):
        self.undo.undo_exp()

    