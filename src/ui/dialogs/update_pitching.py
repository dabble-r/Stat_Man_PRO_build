from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt
from src.ui.styles.stylesheets import StyleSheets
from src.ui.logic.dialogs.update_pitching_logic import (
    check_games_played_for_enablement,
    update_stats,
    undo_stat,
    view_player_stats
)

# --------------------------------------------------

class UpdatePitchingDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        """Pitching stat updater dialog; applies validated deltas to a selected player."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.message = message
        self.setWindowTitle("Update Pitching")
        self.resize(400, 300)
        # self.styles = StyleSheets()
        #self.setStyleSheet(self.styles.modern_styles)
        
        # Widgets
        self.int_label = QLabel("Enter value:")
        self.int_label.setAlignment(Qt.AlignCenter)
        self.int_input = QLineEdit()
        self.int_input.setValidator(QIntValidator())
        self.int_input.setAlignment(Qt.AlignCenter)

        # submit / undo buttons layout 
        self.button_layout = QHBoxLayout()    

        # ----- Submit Button -----
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.update_stats_handler)

        # ----- Undo Button ------
        self.undo_button = QPushButton("Undo")
        self.undo_button.setFixedWidth(100)
        self.undo_button.clicked.connect(self.undo_stat_handler)

        # ----- current view team -------- 
        self.view_team_button = QPushButton("Current\nView")
        self.view_team_button.setFixedWidth(150)
        self.view_team_button.clicked.connect(self.view_player_stats_handler)

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.undo_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.view_team_button, alignment=Qt.AlignCenter)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.int_label)
        form_layout.addWidget(self.int_input)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                            # -----------------------------------------------------------------------------------------------------# 

        # Right side: Radio Buttons in a group
        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []

        #options = ["default"]

        #options = ["games played", "wins", "losses", "games started", "games completed", "shutouts", "saves", "save opportunities", "IP", "at bats", "hits", "runs", "ER", "HR", "HB", "walks", "SO"]

        self.radio_buttons_layout = QVBoxLayout()
        self.radio_buttons_layout.setAlignment(Qt.AlignTop)

        # setup buttons - stat check 
        self.radio_btns_setup()
        
        # Container widget for the radio buttons (optional)
        self.radio_buttons_widget = QWidget()
        self.radio_buttons_widget.setLayout(self.radio_buttons_layout)

                                # --------------------------------------------------------------------------------------------------------------------- #
        
                                # --------------------------------------------------------------------------------------------------------------------- #


        # Horizontal layout: form on the left, radios on the right
        content_layout = QHBoxLayout()
        content_layout.addStretch()
        content_layout.addWidget(form_widget)
        content_layout.addSpacing(40)  # spacing between form and radios
        content_layout.addWidget(self.radio_buttons_widget)
        content_layout.addStretch()

         # ----- Main Layout -----
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(self.button_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)
    
    # experimental
    # check for existing stats
    # enable/disable radio btns according to existing stats
    def radio_btns_stat_check(self):
        """Enable radios if the selected player already has any pitching activity."""
        player, team, num = self.selected
        find_team = self.league.find_team(team)
        if find_team:
            find_player = find_team.get_player(player)
            if find_player:
                if check_games_played_for_enablement(find_player.games_played):
                    self.enable_buttons()
    
    def radio_btns_setup(self):
        """Create and configure radio buttons for supported pitching stat updates."""
        options = ["default"]
        options = ["games played", "wins", "losses", "games started", "games completed", "shutouts", "saves", "save opportunities", "IP", "at bats", "hits", "runs", "ER", "HR", "HB", "walks", "SO"]
        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            if options[i] == 'games played':
                radio.setChecked(True)
            else:
                radio.setEnabled(False)
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            self.radio_buttons_layout.addWidget(radio)
        self.radio_btns_stat_check()

    
    def enable_buttons(self):
        """Enable all radio buttons after a prerequisite stat exists."""
        for el in self.radio_buttons:
            el.setEnabled(True)

    def get_player_stat(self):
        """Return the currently selected radio stat label (as displayed)."""
        # radio button selection 
        selection = self.radio_group.checkedButton().text()
        return selection
    
    def update_stats_handler(self): 
        if update_stats(self.selected, self.get_player_stat(), self.int_input.text(), self.stack, self.message, self.league, self.enable_buttons):
            self.message.show_message(f"Pitching {self.get_player_stat()} successfully updated!", btns_flag=False, timeout_ms=2000)
        self.int_input.clear()

    def undo_stat_handler(self):
        undo_stat(self.selected, self.undo, self.league, self.message)
        self.message.show_message(f"Pitching {self.get_player_stat()} successfully undone!", btns_flag=False, timeout_ms=2000)
    
    '''def view_player_stats(self):
        self.stat_widget = QDialog(self)
        self.stat_widget.setWindowTitle("Stats")
        self.stat_widget.setModal(True)
        self.stat_layout = QVBoxLayout(self.stat_widget)
       
        #print('selected pitching:', self.selected)

        self.stat_ui = Ui_StatDialog(self.league, self.message, self.selected, parent=self.stat_widget)
        
        self.stat_ui.get_stats(self.selected)

        self.stat_ui.exec()'''

    def view_player_stats_handler(self):
        view_player_stats(self.selected, self.league, self.message, self)



    
