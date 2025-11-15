from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QMessageBox, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy, QTreeWidgetItem
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import QCoreApplication, Qt, QTimer
from src.ui.views.league_view_teams import LeagueViewTeams
from src.ui.logic.dialogs.update_positions_logic import set_positions_team, update_stats

from src.ui.styles.stylesheets import StyleSheets
import random

class UpdatePositionsDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        """Dialog to assign field positions to a named player on the selected team."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.message = message

        self.setWindowTitle("Update Positions")
        self.resize(400, 300)
        
        # Widgets
        # player input - lineup
        self.player_label = QLabel("Enter Player:")
        self.player_label.setAlignment(Qt.AlignCenter)
        self.player_input = QLineEdit()
        self.player_input.setAlignment(Qt.AlignCenter)

        # ----- Submit Button ----- #
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.update_stats_handler)

        # ----- Undo Button ------
        self.undo_button = QPushButton("Undo")
        self.undo_button.setFixedWidth(100)
        self.undo_button.clicked.connect(self.undo_stat)

        self.button_layout = QHBoxLayout()

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.undo_button, alignment=Qt.AlignCenter)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.player_label)
        form_layout.addWidget(self.player_input)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                            # -----------------------------------------------------------------------------------------------------# 

        # Right side: Radio Buttons in a group
        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []

        options = ["default"]

        options = ["pitcher", "catcher", "first base", "second base", "third base", "shortstop", "left field", "center field", "right field"]

        radio_buttons_layout = QVBoxLayout()
        radio_buttons_layout.setAlignment(Qt.AlignTop)

        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            radio_buttons_layout.addWidget(radio)

        # Container widget for the radio buttons (optional)
        radio_buttons_widget = QWidget()

        radio_buttons_widget.setLayout(radio_buttons_layout)

                                # ---------------------------------------------------------------------------------------------------------------------#

        # Horizontal layout: form on the left, radios on the right
        content_layout = QHBoxLayout()
        content_layout.addStretch()
        content_layout.addWidget(form_widget)
        content_layout.addSpacing(40)  # spacing between form and radios
        content_layout.addWidget(radio_buttons_widget)
        content_layout.addStretch()

         # ----- Main Layout ----- #
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(self.button_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def get_team_pos(self):
        """Return selected position label from radio buttons."""
        # radio button selection 
        selection = self.radio_group.checkedButton().text()
        return selection        
    
    def update_stats_handler(self):
        update_stats(self.selected, self.get_team_pos(), self.player_input.text(), self.stack, self.message, self.league, self=self)
        self.message.show_message("Position successfully updated!", btns_flag=False, timeout_ms=2000)
        self.player_input.clear()
        
    
    def undo_stat(self):
        self.undo.undo_exp()
          
            
            