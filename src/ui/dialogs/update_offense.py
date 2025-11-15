from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QMessageBox, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy, QTreeWidgetItem
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import QCoreApplication, Qt, QTimer
from src.ui.views.league_view_teams import LeagueViewTeams

from src.ui.styles.stylesheets import StyleSheets
from src.core.node import NodeStack
from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog
import random

# New: logic helpers - imported with aliases to avoid name collision with class methods
from src.ui.logic.dialogs.update_offense_logic import (
    coerce_at_bat,
    should_enable_buttons,
    normalize_numeric_fields,
    set_new_stat_player as logic_set_new_stat_player,
    refresh_player as logic_refresh_player,
    refresh_team as logic_refresh_team,
    refresh_leaderboard_logic,
    insert_widget as logic_insert_widget,
    stat_lst as logic_stat_lst,
    build_offense_undo_payload,
    enforce_positive_integer
)

class UpdateOffenseDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, styles, message, parent=None):
        """Offense stat updater dialog; applies validated deltas to a selected player."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.styles = styles
        self.message = message
        #print('update msg isnt', self.message)
        self.setWindowTitle("Update Offense")
        self.resize(400, 300)
        #self.setStyleSheet(self.styles.modern_styles)
        
        # Widgets
        self.int_label = QLabel("Enter value:")
        self.int_label.setAlignment(Qt.AlignCenter)
        self.int_input = QLineEdit()
        self.int_input.setValidator(QIntValidator())
        self.int_input.setAlignment(Qt.AlignCenter)

        # button layout 
        self.button_layout = QVBoxLayout()

        # ----- Submit Button -----
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(125)
        self.submit_button.clicked.connect(self.update_stats)

        # -------- Undo Button -------
        self.undo_button = QPushButton("Undo")
        self.undo_button.setFixedWidth(100)
        self.undo_button.clicked.connect(self.undo_stat)

        # --------curr stat snapshot ------- 
        self.view_player_button = QPushButton("Current\nView")
        self.view_player_button.setFixedWidth(150)
        self.view_player_button.clicked.connect(self.view_player_stats)

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.undo_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.view_player_button, alignment=Qt.AlignCenter)

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

        
        self.radio_buttons_layout = QVBoxLayout()
        self.radio_buttons_layout.setAlignment(Qt.AlignTop)

        
        
        self.radio_btns_setup()

        # Container widget for the radio buttons (optional)
        self.radio_buttons_widget = QWidget()
        self.radio_buttons_widget.setLayout(self.radio_buttons_layout)

                                # ---------------------------------------------------------------------------------------------------------------------#
                                                                # stat UI and widget setup #
        self.stat_widget = QDialog(self)
        self.stat_widget.setWindowTitle(f"Stats")
        self.stat_widget.setModal(True)
        self.stat_layout = QVBoxLayout(self.stat_widget)
        

                                # ---------------------------------------------------------------------------------------------------------------------#

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
        main_layout.addLayout(self.button_layout, stretch=5)
        main_layout.addStretch()

        self.setLayout(main_layout)

                        #----------------------------------------------------------------------------------------------------------------#
    # experimental
    # check for existing stats
    # enable/disable radio btns according to existing stats
    def radio_btns_stat_check(self):
        """Enable radios if selected player already has at-bats; otherwise keep minimal set."""
        player, team, num = self.selected
        find_team = self.league.find_team(team)
        if find_team:
            find_player = find_team.get_player(player)
            if find_player:
                at_bat = coerce_at_bat(getattr(find_player, 'at_bat', 0))
                if should_enable_buttons(at_bat):
                    print('stats exist')
                    self.enable_buttons()
    
    def radio_btns_setup(self):
        """Create and configure offense radio buttons for supported stat updates."""
        options = ["hit", "bb", "hbp", "so", "put out", "hr", "rbi", "runs", "singles", "doubles", "triples", "sac fly", "fielder's choice"]

        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            if options[i] == 'hit':
                radio.setChecked(True)
            else:
                radio.setEnabled(False)
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            self.radio_buttons_layout.addWidget(radio)
        self.radio_btns_stat_check()

    def enable_buttons(self):
        """Enable all radio buttons after a prerequisite stat exists (e.g., hits/AB present)."""
        for el in self.radio_buttons:
            el.setEnabled(True)

    def get_player_stat(self):
        """Return the currently selected radio stat label (as displayed)."""
        # radio button selection 
        selection = self.radio_group.checkedButton().text()
        return selection
    
    def set_new_stat_player(self, stat, val, player):
        """Route chosen offense stat to the matching setter on the player instance."""
        logic_set_new_stat_player(stat, val, player, enable_buttons_callback=self.enable_buttons)

    def update_stats(self):
        """Validate selection and value, update offense stats, and push to the undo stack."""
        stat = None
        val = None

        try:
            stat = self.get_player_stat()
        except:
            self.message.show_message("Must select a player stat to update.", btns_flag=False, timeout_ms=2000)
            #QMessageBox.warning(self, "Input Error", "Must select a player stat to update.")
            return

        if not stat or not self.int_input.text():
            self.message.show_message("Please enter value and select stat.", btns_flag=False, timeout_ms=2000)
            #QMessageBox.warning(self, "Input Error", "Please enter value and select stat.")
            return
        
        #val = int(self.int_input.text())
        val = enforce_positive_integer(self.int_input.text(), self.message)

        player, team, avg = self.selected
        find_team = self.league.find_team(team)
        if not find_team:
            self.message.show_message("Selected team is no longer available. Refresh and try again.", btns_flag=False, timeout_ms=2000)
            return
        find_player = find_team.get_player(player)
        if not find_player:
            self.message.show_message("Selected player is no longer available. Refresh and try again.", btns_flag=False, timeout_ms=2000)
            return

        # Normalize numeric fields on the target player to avoid string concatenation
        try:
            numeric_fields = ['pa','at_bat','fielder_choice','hit','bb','hbp','put_out','so','hr','rbi','runs','singles','doubles','triples','sac_fly']
            normalize_numeric_fields(find_player, numeric_fields)
        except Exception:
            pass

        # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
        # stat hierarchy:  
            # radio buttons options 
            # radio selection 
            # exact player attr/stat passed to stack node 
            # stat passed to set new stat 
            # stat updated on player instance
        stat_result = logic_stat_lst(stat, val)
        
        statType = build_offense_undo_payload(stat_result)

        print("stat result-type:", statType)

        self.stack.add_node(find_player, team, stat_result, getattr(find_player, statType), self.set_new_stat_player, 'player')

        self.set_new_stat_player(statType, int(val), find_player)

        logic_refresh_player(find_player)

        self.leaderboard.refresh_leaderboard(find_player)
        
        find_team.set_bat_avg()

        self.refresh_leaderboard(find_team, self.lv_teams.tree2_bottom)
        #self.insert_end_avg(find_team)

    def refresh_leaderboard(self, team_upd, view):
        """Update leaderboard: refresh list logic and populate widget."""
        refresh_leaderboard_logic(self.league, team_upd, self.leaderboard_AVG)
        logic_insert_widget(view, self.leaderboard_AVG)

    def undo_stat(self):
        """Execute undo operation and refresh all affected views."""
        player, team, avg = self.selected
        find_team = self.league.find_team(team)
        if find_team:
            find_player = find_team.get_player(player)
            if find_player:
                self.undo.undo_exp(self.message)
                logic_refresh_player(find_player)
                logic_refresh_team(find_team)
                self.leaderboard.refresh_leaderboard(find_player)
                self.refresh_leaderboard(find_team, self.lv_teams.tree2_bottom)

    def view_player_stats(self):
        #print("view stats")
        ##print('selected:', self.selected)
        
        #self.stat_ui.populate_stats(self.selected)
        # last attmept - not functional for player
        #self.stat_ui.get_stats(self.selected)
        self.stat_ui = Ui_StatDialog(self.league, self.message, self.selected, parent=self.stat_widget)
        self.stat_ui.get_stats(self.selected)
        self.stat_ui.exec()
