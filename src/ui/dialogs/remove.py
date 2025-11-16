from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QMessageBox, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy, QTreeWidgetItem
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import QCoreApplication, Qt, QTimer
from src.ui.views.league_view_teams import LeagueViewTeams
from src.core.linked_list import LinkedList

import random

class RemoveDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, lv_players, parent=None):
        """Dialog to remove a selected team/player from current view or entire league."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.lv_players = lv_players

        # ----- Submit Button -----
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.remove_item)

        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []

        options = ["League", "Current View"]

        radio_buttons_layout = QVBoxLayout()
        radio_buttons_layout.setAlignment(Qt.AlignTop)
        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            radio.setChecked(True)
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
        content_layout.addWidget(radio_buttons_widget)
        content_layout.addStretch()

                            # -----------------------------------------------------------------------------------------------------# 

        # ----- Main Layout ----- #
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addSpacing(20)
        main_layout.addLayout(content_layout)
        main_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)

        self.setLayout(main_layout)

    def get_radio_selection(self):
        """Return radio selection label determining removal scope (League/Current View)."""
        selection = self.radio_group.checkedButton().text()
        return selection

    def remove_current_view(self):
        """Remove the selected item from visible views only, keeping league data intact."""
        #print('current view') 

        if not self.league.teams:
            #print('no teams in league')
            return 
        
        #print('selection:', self.selected)

        if len(self.selected) == 2:
            team, avg = self.selected
            find_team = self.league.find_team(team)
            
            if find_team:
              self.lv_teams.remove_league_view_wl(find_team)
              self.lv_teams.remove_league_view_avg(find_team)

        elif len(self.selected) == 3:
            player, team, avg = self.selected
            find_team = self.league.find_team(team)
            find_player = find_team.get_player(player)

            if find_player:
                self.lv_players.remove_league_view(find_player)
                self.leaderboard.remove_handler(find_player)

        #print('league after:', self.league)
    
    def remove_league(self):
        """Remove the selected team or player from the league after confirmation."""
        #print('league before:', self.league)

        if not self.league.teams:
            #print('no teams in league')
            return 
        
        #print('selection:', self.selected)

        if len(self.selected) == 2:
            ques = QMessageBox(self)
            ques.setWindowTitle("Confirm Action")
            ques.setText("Do you want to remove team and all associated players?")
            ques.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            ques.setDefaultButton(QMessageBox.Cancel)

            result = ques.exec()
            if result == QMessageBox.Cancel:
                return

            team, avg = self.selected
            print(f"\n=== REMOVE TEAM - DEBUG ===")
            print(f"Selected team name: '{team}'")
            print(f"Team count before removal: {len(self.league.teams)}")
            print(f"All teams in league: {[t.name for t in self.league.get_all_objs()]}")
            
            find_team = self.league.find_team(team)
            print(f"Found team object: {find_team.name if find_team else 'None'}")

            if find_team:
                print(f"Team has {len(find_team.players)} players: {[p.name for p in find_team.players]}")
                
                self.lv_teams.remove_league_view_wl(find_team)
                self.lv_teams.remove_league_view_avg(find_team)

                team_players = find_team.players
                for el in team_players:
                    self.lv_players.remove_league_view(el)
                    self.leaderboard.refresh_leaderboard_removal(el)
                
                print(f"About to call self.league.remove_team('{team}')")
                self.league.remove_team(team)
                print(f"Team count after removal: {len(self.league.teams)}")
                print(f"All teams remaining: {[t.name for t in self.league.get_all_objs()]}")
                print("=== END DEBUG ===\n") 

        elif len(self.selected) == 3:
            ques = QMessageBox(self)
            ques.setWindowTitle("Confirm Action")
            ques.setText("Do you want to remove player and all stats permanently?")
            ques.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            ques.setDefaultButton(QMessageBox.Cancel)

            result = ques.exec()
            if result == QMessageBox.Cancel:
                return

            player, team, avg = self.selected
            find_team = self.league.find_team(team)
            find_player = find_team.get_player(player)

            if find_player:
                find_team.remove_player(player)
                self.lv_players.remove_league_view(find_player)
                self.leaderboard.remove_handler(find_player)

        #print('after removal:', self.league)
                
    def remove_item(self):
        selection = self.get_radio_selection()
        if selection == "Current View":
            ##print('current')
            self.remove_current_view()
        elif selection == "League":
            ##print('league')
            self.remove_league()
        self.close()