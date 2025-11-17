# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_save.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget, QDialog)
from src.ui.dialogs.new_player_ui import Ui_NewPlayer
from src.ui.dialogs.new_team_w_ui import Ui_NewTeam
from src.data.save.save_dialog import SaveDialog

class Ui_Add_Save(QWidget, object):
    def __init__(self, leaderboard, players=None, teams_AVG=None, teams_WL=None):
        """Toolbar widget to add players/teams and open save dialog from main views."""
        super().__init__()
        self.league_view_players = players 
        self.league_view_teams_AVG = teams_AVG
        self.league_view_teams_WL = teams_WL
        self.leaderboard = leaderboard

    def setupUi(self, add_save):
        """Build the buttons and wire handlers for add player/team and save actions."""
        if not add_save.objectName():
            add_save.setObjectName(u"add_save")
        add_save.resize(400, 300)
        self.widget = QWidget(add_save)
        self.widget.setObjectName(u"widget")
        self.widget.setGeometry(QRect(75, 80, 77, 86))
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.add_player = QPushButton(self.widget)
        self.add_player.setObjectName(u"add_player")
        self.add_player.clicked.connect(self.new_player_handler)
        

        self.verticalLayout.addWidget(self.add_player)

        self.add_team = QPushButton(self.widget)
        self.add_team.setObjectName(u"add_team")
        self.add_team.clicked.connect(self.new_team_handler)

        self.verticalLayout.addWidget(self.add_team)

        self.save = QPushButton(self.widget)
        self.save.setObjectName(u"save")
        self.save.clicked.connect(self.save_handler)

        self.verticalLayout.addWidget(self.save)

        self.retranslateUi(add_save)

        QMetaObject.connectSlotsByName(add_save)

    def new_player_handler(self):
        """Open the New Player dialog pre-wired with leaderboard references."""
        print("add new player")
        self.new_player_ui = Ui_NewPlayer(league_view=self.league_view_players, leaderboard=self.leaderboard)
        self.new_player_widget = QDialog()
        self.new_player_ui.setupUi(self.new_player_widget)
        self.new_player_widget.setWindowTitle("Add New Player")
        self.new_player_widget.setModal(True)
        self.new_player_widget.exec()
    
    def new_team_handler(self):
        """Open the New Team dialog tied to AVG/WL team views."""
        print("add new team")
        self.new_team_ui = Ui_NewTeam(self.league_view_teams_AVG, self.league_view_teams_WL)
        self.new_team_widget = QDialog()
        self.new_team_ui.setupUi(self.new_team_widget)
        self.new_team_widget.setWindowTitle("Add New Team")
        self.new_team_widget.setModal(True)
        self.new_team_widget.exec()
    
    def save_handler(self):
        """Launch Save dialog using league/message from players view; guard nulls."""
        print('saving progress')
        # Get league, message, and file_dir from league_view_players
        league = self.league_view_players.league if hasattr(self.league_view_players, 'league') else None
        message = self.league_view_players.message if hasattr(self.league_view_players, 'message') else None
        file_dir = self.league_view_players.file_dir if hasattr(self.league_view_players, 'file_dir') else "data"
        
        if not league or not message:
            print("Error: Cannot save - league or message not available")
            return
        
        # Use the correct SaveDialog class with required parameters
        self.save_widget = SaveDialog(league, message, file_dir, parent=None)
        self.save_widget.setModal(True)
        self.save_widget.exec()

    # setupUi

    def retranslateUi(self, add_save):
        add_save.setWindowTitle(QCoreApplication.translate("add_save", u"Form", None))
        self.add_player.setText(QCoreApplication.translate("add_save", u"Add Player", None))
        self.add_team.setText(QCoreApplication.translate("add_save", u"Add Team", None))
        self.save.setText(QCoreApplication.translate("add_save", u"SAVE", None))
    # retranslateUi

