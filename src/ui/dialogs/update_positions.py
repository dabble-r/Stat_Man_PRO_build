from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QMessageBox, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy, QTreeWidgetItem
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import QCoreApplication, Qt, QTimer
from src.ui.views.league_view_teams import LeagueViewTeams

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
        self.styles = StyleSheets()
        self.setStyleSheet(self.styles.modern_styles)
        
        # Widgets
        # player input - lineup
        self.player_label = QLabel("Enter Player:")
        self.player_label.setAlignment(Qt.AlignCenter)
        self.player_input = QLineEdit()
        self.player_input.setAlignment(Qt.AlignCenter)

        # ----- Submit Button ----- #
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.update_stats)

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

    def set_positions_team(self, pos, player, team):
        """Apply the given position to team using team.set_pos with confirmation prompts."""
        '''"pitcher", "catcher", "first base", "second base", "third base", "shortstop", "left field", "center field", "right field"'''
        match pos:
            case 'pitcher':
                team.set_pos('positions', pos, player, self)
            case 'catcher':
                team.set_pos('positions', pos, player, self)
            case 'first base':
                team.set_pos('positions', pos, player, self)
            case 'second base':
                team.set_pos('positions', pos, player, self)
            case 'third base':
                team.set_pos('positions', pos, player, self)
            case 'shortstop':
                team.set_pos('positions', pos, player, self)
            case 'left field':
                team.set_pos('positions', pos, player, self)
            case 'center field':
                team.set_pos('positions', pos, player, self)
            case 'right field':
                team.set_pos('positions', pos, player, self)

    def update_stats(self):
        """Validate inputs, push to undo stack, and update team position assignment."""
        pos = self.get_team_pos()
        player = self.player_input.text()
        team, avg = self.selected
        find_team = self.league.find_team(team)

        if not pos or not player:
            #QMessageBox.warning(self, "Input Error", "Enter player name and select position.")
            self.message.show_message("Enter player name and select position.")
            return 
     
        ##print('team before:', find_team)

        # stack add node 
        # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
        self.stack.add_node(find_team, team, 'positions', (pos, find_team.positions[pos]), self.set_positions_team, 'team')

        self.set_positions_team(pos, player, find_team)

        ##print('team after:', find_team.return_stats())

        ###print('team after:', find_team)
    
    def undo_stat(self):
        self.undo.undo_exp()
          
            
            