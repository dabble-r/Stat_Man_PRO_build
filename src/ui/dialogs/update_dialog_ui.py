from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt
from src.ui.dialogs.update_offense import UpdateOffenseDialog
from src.ui.dialogs.update_pitching import UpdatePitchingDialog
from src.ui.dialogs.update_admin import UpdateAdminDialog
from src.ui.dialogs.update_team_stats import UpdateTeamStatsDialog
from src.utils.file_dialog import FileDialog
from src.utils.image import Icon

# New: logic helpers
from src.ui.logic.dialogs.update_dialog_logic import (
    player_has_pitching,
    set_team_logo,
    set_player_image,
)

class UpdateDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, file_dir, styles, message, parent=None):
        """Hub dialog for updating players/teams (offense, pitching, admin, team stats)."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.file_dir = file_dir
        self.styles = styles
        self.message = message
        self.parent = parent
        self.setObjectName("Update Dialog")

        # Widgets
        self.int_label = QLabel("Enter value:")
        self.int_label.setAlignment(Qt.AlignCenter)
        self.int_input = QLineEdit()
        self.int_input.setValidator(QIntValidator())
        self.int_input.setAlignment(Qt.AlignCenter)

        # player stat buttons
        # stat category 
        self.offense_button = QPushButton("Offense")
        #self.offense_button.setFixedWidth(150)
        self.offense_button.clicked.connect(self.update_offense_handler)

        self.pitching_button = QPushButton("Pitching")
        #self.pitching_button.setFixedWidth(150)
        self.pitching_button.clicked.connect(self.update_pitching_handler)

        # team admin buttons 
        # stat category 
        self.admin_button = QPushButton("Management")
        self.admin_button.setFixedWidth(250) 
        self.admin_button.clicked.connect(self.update_admin_handler)

        # team stats buttons 
        # stat category 
        self.team_stats_button = QPushButton("Stats")
        self.team_stats_button.setFixedWidth(100) 
        self.team_stats_button.clicked.connect(self.update_team_stats_handler)

        # team stats buttons 
        # logo category 
        self.upload_button = QPushButton("Upload")
        self.upload_button.setFixedWidth(100) 
        self.upload_button.clicked.connect(self.upload_handler)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.int_label)
        form_layout.addWidget(self.int_input)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                            # -----------------------------------------------------------------------------------------------------# 

        # ----- Main Layout -----
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addSpacing(20)

        self.resize(400, 300)

        if len(self.selected) == 2:
            self.setWindowTitle("Update Team")

            main_layout.addWidget(self.admin_button, alignment=Qt.AlignCenter)
            main_layout.addWidget(self.team_stats_button, alignment=Qt.AlignCenter)
            main_layout.addWidget(self.upload_button, alignment=Qt.AlignCenter)

            self.setLayout(main_layout)

        else:
            self.setWindowTitle("Update Player")

            main_layout.addWidget(self.offense_button, alignment=Qt.AlignCenter)
            main_layout.addWidget(self.pitching_button, alignment=Qt.AlignCenter)
            main_layout.addWidget(self.upload_button, alignment=Qt.AlignCenter)

            self.setLayout(main_layout)

    def update_offense_handler(self):
        """Open the offense update dialog for the selected player."""
        dialog = UpdateOffenseDialog(self.league, self.selected, self.leaderboard, self.lv_teams, self.stack, self.undo, self.styles, self.message, parent=self)
        dialog.setStyleSheet("QDialog { border: 2px solid black; }")
        dialog.exec()
    
    def update_pitching_handler(self):
        """Open the pitching update dialog if player has 'pitcher' in positions."""
        player, team, avg = self.selected
        find_team = self.league.find_team(team)
        find_player = find_team.get_player(player)
        if not player_has_pitching(getattr(find_player, 'positions', [])):
            self.message.show_message("Player has no pitching position.", btns_flag=False, timeout_ms=2000)
        else:
            dialog = UpdatePitchingDialog(self.league, self.selected, self.leaderboard, self.lv_teams, self.stack, self.undo, self.message, parent=self)
            dialog.exec()
    
    def update_admin_handler(self):
        """Open management/admin dialog to edit team admin fields."""
        dialog = UpdateAdminDialog(self.league, self.selected, self.leaderboard, self.lv_teams, self.stack, self.undo, self.message, parent=self)
        dialog.exec()

    def update_team_stats_handler(self):
        """Open team stats dialog for computed/display team statistics."""
        dialog = UpdateTeamStatsDialog(self.league, self.selected, self.leaderboard, self.lv_teams, self.stack, self.undo, self.message, self.styles, parent=self)
        dialog.exec()
    
    def upload_dialog(self):
        """Open file picker, build icon from selected path, and apply to current team/player."""
        dialog = FileDialog(self.message, parent=self, flag='save')
        dialog.open_file_dialog()
        file_path = dialog.get_file_path()
        icon = self.get_icon(file_path)
        if len(self.selected) == 2 and icon is not None:
            self.change_logo(icon)
        return icon, file_path

    def get_icon(self, file_path):
        icon = Icon(file_path)
        ret_icon = icon.create_icon()
        return ret_icon
    
    def upload_handler(self):
        icon = None

        if len(self.selected) == 2:
            team, avg = self.selected
            try:
                icon, file_path = self.upload_dialog()
                find_team = self.league.find_team(team)
                set_team_logo(find_team, file_path)
                self.message.show_message("Team logo successfully updated!", btns_flag=False, timeout_ms=2000)
            except Exception as e:
                self.message.show_message(f"Error uploading logo!", btns_flag=False, timeout_ms=2000)

        elif len(self.selected) == 3: 
            player, team, avg = self.selected
        
            try:
                icon, file_path = self.upload_dialog()
                find_team = self.league.find_team(team)
                find_player = find_team.get_player(player)
                set_player_image(find_player, file_path)
                self.message.show_message("Player image successfully updated!", btns_flag=False, timeout_ms=2000)
            except Exception as e:
                self.message.show_message(f"Error uploading image!", btns_flag=False, timeout_ms=2000)
        
        return
    
    def change_logo(self, new_logo):
        # iterate thru stack of widget items 
        # match item name 
        # delete item from widget 
        # replace item with updated item and new logo
        team, num = self.selected

        curr_1 = self.lv_teams.tree1_bottom.currentItem()
        curr_2 = self.lv_teams.tree2_bottom.currentItem()
        
        if curr_1:
            curr_1.setIcon(0, new_logo)
            team = curr_1.text(0)
            self.refresh_other(self.lv_teams.tree2_bottom, team, new_logo)
        elif curr_2:
            curr_2.setIcon(0, new_logo)
            team = curr_2.text(0)
            self.refresh_other(self.lv_teams.tree1_bottom, team, new_logo)
        
    def refresh_other(self, widget, team, logo):
        # itereate through widget 
        # find matching team name 
        # set icon to new logo
        for i in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(i)
            name = item.text(0)
            if name == team:
                item.setIcon(0, logo)
            
                        #----------------------------------------------------------------------------------------------------------------#
    
     