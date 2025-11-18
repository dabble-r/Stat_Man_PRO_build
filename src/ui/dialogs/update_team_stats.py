from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt
from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog
from src.ui.views.tab_widget import TabWidget
from src.ui.logic.dialogs.update_team_stats_logic import (
    refresh_team_derived_stats,
    update_leaderboard_wl_item,
)

# --------------------------------------------------

class UpdateTeamStatsDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, styles, parent=None):
        """Dialog to edit team-level stats (games/wins/losses) and view aggregates."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.message = message
        self.styles = styles
        self.parent = parent
        self.setWindowTitle("Update Management")
        self.resize(500, 300)
        #self.styles = StyleSheets()
        #self.setStyleSheet(self.styles.main_styles)

        # Widgets
        self.int_label = QLabel("Enter value:")
        self.int_label.setAlignment(Qt.AlignCenter)
        self.int_input = QLineEdit()
        self.int_input.setValidator(QIntValidator())
        self.int_input.setAlignment(Qt.AlignCenter)

        # ----- Submit Button -----
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.update_stats)

        # -------- Undo Button -------
        self.undo_button = QPushButton("Undo")
        self.undo_button.setFixedWidth(100)
        self.undo_button.clicked.connect(self.undo_stat)

         # -------- View Team Stats Button -------
        self.view_team_stats_button = QPushButton("Current\nView")
        self.view_team_stats_button.setFixedWidth(150)
        self.view_team_stats_button.clicked.connect(self.view_team_stats)

        # ------ buttons layout ------ #
        self.buttons_layout = QHBoxLayout()

        self.buttons_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.buttons_layout.addWidget(self.undo_button, alignment=Qt.AlignCenter)
        self.buttons_layout.addWidget(self.view_team_stats_button, alignment=Qt.AlignCenter)

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

        options = ["default"]

        # "game stats" option removed
        options = ["games played", "wins", "losses"]

        radio_buttons_layout = QVBoxLayout()
        radio_buttons_layout.setAlignment(Qt.AlignTop)

        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            if options[i] == 'games played':
                radio.setChecked(True)
            else: 
                radio.setEnabled(False)
            radio.toggled.connect(self.render_input_form)
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            radio_buttons_layout.addWidget(radio)

        # Container widget for the radio buttons (optional)
        radio_buttons_widget = QWidget()
        radio_buttons_widget.setLayout(radio_buttons_layout)

                                # ---------------------------------------------------------------------------------------------------------------------#
        
        
        self.stat_widget = QDialog(self)
        #self.stat_widget.setStyleSheet(self.styles.modern_styles)

                                # ---------------------------------------------------------------------------------------------------------------------#

        # Horizontal layout: form on the left, radios on the right
        content_layout = QHBoxLayout()
        content_layout.addStretch()
        content_layout.addWidget(form_widget)
        content_layout.addSpacing(40)  # spacing between form and radios
        content_layout.addWidget(radio_buttons_widget)
        content_layout.addStretch()

         # ----- Main Layout -----
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(self.buttons_layout)
        main_layout.addStretch()

        self.setLayout(main_layout) 
    
    def enable_buttons(self):
        for el in self.radio_buttons:
            el.setEnabled(True)

    def render_input_form(self):
        text = self.radio_group.checkedButton().text()
        if text == "game stats":
            #self.int_input.hide()
            pass
        else:
            self.int_input.show()
            

    def get_team_stat(self):
        # radio button selection 
        selection = self.radio_group.checkedButton().text()
        return selection        

    def set_new_stat_team(self, stat, val, team):
        '''"wins, losses, games played"'''
        match stat:
            case 'wins':
                team.set_wins(val, self)
            case 'losses':
                team.set_losses(val, self)
            case 'games_played':
                team.set_games_played(val, self)
                self.enable_buttons()
            case 'game stats':
                pass

    def update_stats(self):
        stat = None 
        val = None
        
        team, avg = self.selected
        find_team = self.league.find_team(team)

        try:
            stat = self.get_team_stat()
            val = int(self.int_input.text())
            if not stat or not val:
                #QMessageBox.warning(self, "Input Error", "Enter value and select stat.")
                self.message.show_message("Enter value and select stat.", btns_flag=False, timeout_ms=2000)
                return 
            
        except:
            #QMessageBox.warning(self, "Input Error", "Enter value and select stat.")
            self.message.show_message("Enter value and select stat.", btns_flag=False, timeout_ms=2000)
            return 
        
            ###print('team before:', find_team)

        # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
        # stat hierarchy:  
            # radio buttons options 
            # radio selection 
            # exact player attr/stat passed to stack node 
            # stat passed to set new stat 
            # stat updated on player instance
        if stat == 'game stats':
            self.update_game_handler()
            return

        if stat == 'games played':
            stat = stat.replace(" ", "_")

        self.stack.add_node(find_team, team, stat, getattr(find_team, stat), self.set_new_stat_team, 'team')

        self.set_new_stat_team(stat, val, find_team)

        refresh_team_derived_stats(find_team)

        self.refresh_leaderboard_wl(find_team)

        ##print('stack after:', self.stack)
    
    def refresh_team_stats(self, team):
        """Legacy wrapper; now delegates to logic module."""
        refresh_team_derived_stats(team)
    
    def refresh_leaderboard_wl(self, target):
        """Update W-L leaderboard item for the target team."""
        count = self.lv_teams.tree1_bottom.topLevelItemCount()
        team_target = target.name
        wl_upd = target.get_wl_avg()
        i = 0
        while i < count:
            item = self.lv_teams.tree1_bottom.topLevelItem(i)
            if update_leaderboard_wl_item(item, team_target, wl_upd):
                break
            i += 1
    
    def undo_stat(self):
        team, avg = self.selected
        find_team = self.league.find_team(team)
        if find_team:
            self.undo.undo_exp()
            refresh_team_derived_stats(find_team)
            self.refresh_leaderboard_wl(find_team)

    def view_team_stats(self):
        ##print("view stats")
        ###print('selected:', self.selected)
        #self.stat_ui.setupUi(self.stat_widget)
        #self.stat_widget.setWindowTitle(f"Stats")
        #self.stat_widget.setModal(True)
        #self.stat_ui.populate_stats(self.selected)
        #self.stat_ui.get_stats(self.selected)
        #self.stat_ui.get_stats()
        #self.stat_widget.exec()
        #print('selected before:', self.selected)
        self.stat_ui = Ui_StatDialog(self.league, self.message, self.selected, parent=self.stat_widget)
        self.stat_ui.get_stats(self.selected)
        self.stat_ui.exec()
        #print('selected after:', self.selected)

    def update_game_handler(self):
        #dialog = UpdateGameDialog(self.league, self.selected, self.leaderboard, self.lv_teams, self.stack, self.undo, self.message, parent=self)
        #dialog.exec()
        ##print('tab widget')
        #tab_widget = TabWidget('Default Title')
        dialog = QDialog(self)
        dialog.resize(500, 750)

        self.tab_widget = TabWidget('Game Stats')
        self.tab_widget.create_tab(1, 1, 'Tab 1')
        self.tab_widget.create_tab(2, 2, 'Tab 2')
        self.tab_widget.create_tab(3, 3, 'Tab 3')

        self.tab_widget.enable_tabs()
        self.tab_widget.setFocusPolicy(Qt.StrongFocus)

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.addWidget(self.tab_widget)
        dialog.setLayout(dialog_layout)
        dialog.exec()  # or dialog.show()

            
            