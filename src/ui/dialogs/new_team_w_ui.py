# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_team_w.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon, QIntValidator,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QSpacerItem,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget, QTreeWidget, QTreeWidgetItem, QMessageBox)
from src.core.team import Team
from src.utils.image import Icon
from src.utils.file_dialog import FileDialog

import random

class Ui_NewTeam(QWidget, object):
    def __init__(self, league_view_WL, league_view_AVG, league, file_dir, styles, message, parent=None):
        """Form/dialog to create a new team, set name/logo, and add to league views."""
        super().__init__(parent)
        self.league_view_WL = league_view_WL
        self.league_view_AVG = league_view_AVG
        self.league = league
        self.logo = None
        self.file_path = None
        self.file_dir = file_dir
        self.styles = styles
        self.message = message
        self.parent = parent
        
    def setupUi(self, AddTeam):
        """Build the New Team UI and wire inputs for name/logo creation and submission."""
        if not AddTeam.objectName():
            AddTeam.setObjectName(u"AddTeam")
        AddTeam.resize(500, 450)

        self.widget = QWidget(AddTeam)
        self.widget.setObjectName(u"widget")
        #self.widget.setGeometry(QRect(80, 60, 241, 141))
        self.widget.setMinimumSize(450, 400)
        
        self.label = QLabel()
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(170, 20, 150, 20))


        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout.setSpacing(2)


        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")

        self.label_2 = QLabel(self.widget)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.name = QLineEdit(self.widget)
        self.name.setFocus()
        self.name.setFixedWidth(275)
        self.name.setObjectName(u"name")

        self.horizontalLayout.addWidget(self.name)

        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout.addStretch(1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")

        self.label_3 = QLabel(self.widget)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_2.addWidget(self.label_3)

        self.max_roster = QLineEdit(self.widget)
        self.max_roster.setValidator(QIntValidator())
        self.max_roster.setFixedWidth(275)
        self.max_roster.setObjectName(u"max_roster")

        self.horizontalLayout_2.addWidget(self.max_roster)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout.addStretch(1)


        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")

        self.label_5 = QLabel(self.widget)
        self.label_5.setObjectName(u"label_5")

        self.manager = QLineEdit(self.widget)
        self.manager.setObjectName(u"manager")
        self.manager.setFixedWidth(275)

        self.horizontalLayout_4.addWidget(self.label_5)
        self.horizontalLayout_4.addWidget(self.manager)
        
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.verticalLayout.addStretch(1)


        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        
        self.label_4 = QLabel(self.widget)
        
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_3.addWidget(self.label_4)

        self.button_upload = QPushButton(self.widget)
        self.button_upload.setObjectName(u"upload_button")
        self.button_upload.setFixedHeight(50)
        self.button_upload.clicked.connect(self.button_upload_handler)

        self.horizontalLayout_3.addWidget(self.button_upload)

        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.verticalLayout.addStretch(5)

        self.verticalLayout_upload = QVBoxLayout()
        self.button_submit = QPushButton()
        self.button_submit.setObjectName(u"submit_button")
        self.button_submit.setMaximumWidth(125)
        #self.button_submit.setFixedHeight(50)
        #self.button_submit.setFixedWidth(125)
        self.button_submit.clicked.connect(self.new_team_handler)
        self.verticalLayout_upload.addStretch()
        self.verticalLayout_upload.addWidget(self.button_submit, alignment=Qt.AlignRight)
        self.verticalLayout_upload.addStretch() 

        self.verticalLayout.addLayout(self.verticalLayout_upload)

        self.main_layout = QVBoxLayout(AddTeam)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.main_layout.addWidget(self.label, alignment=Qt.AlignCenter)
        self.main_layout.addWidget(self.widget)

        self.retranslateUi(AddTeam)

        QMetaObject.connectSlotsByName(AddTeam)
    # setupUi

    def clear_all(self):
        self.name.clear()
        self.manager.clear()
        self.max_roster.clear()
    
    def check_dups(self, team):
        find_team = self.league.find_team(team)
        if find_team:
            return True 
        return False
    
    def check_input(self):
        ret = (1, "new team added")

        if not self.name.text() or not self.manager.text():
            ret = (0, "Complete all fields before submitting.")
            return ret 

        elif self.name.text() and self.manager.text():
            try: 
                max = int(self.max_roster.text()) >= 9
                if max:
                    return ret
                ret = (0, "Must enter roster value of 9 or more.")
                return ret
            except:
                ret = (0, "Must enter roster value as number of 9 or more.")
                return ret
        
    def new_team_handler(self):
        ##print("submitting...")
        #self.logo = None 
        #self.file_path = None

        team = self.name.text().strip()

        error = self.check_input()
        if error[0] == 0:
            #QMessageBox.warning(self, "Input Error", f"{error[1]}") 
            self.message.show_message(f"{error[1]}")
            return
        
        elif self.check_dups(team) == True:
            self.message.show_message("Team already exsits!")
            return
        
        # item WL
        new_team = Team(self.league, self.name.text().strip(), self.manager.text().strip(), message=self.message, max_roster=int(self.max_roster.text().strip()))
        # generate default lineup - dict
        # default lineup populated of max roster size        
        
                                                    # ---------------------------------------------------- #
        new_team.populate_lineup()
        
        wl = new_team.get_wl_avg()
        avg = new_team.get_bat_avg()
        vals = [self.name.text(), self.max_roster.text(), str(avg)]
        # ##print(vals)

        ###print("new team:", new_team)
        self.league.add_team(new_team)
        item_WL = QTreeWidgetItem([vals[0], str(wl)])
        item_AVG = QTreeWidgetItem([vals[0], str(avg)])
        
        if self.file_path and self.logo:
            #self.league_view_WL.setColumnCount(3)
            self.update_logo_path(new_team)
            #new_team_logo, file_path = self.get_icon(self.file_path)
            item_WL.setIcon(0, self.logo)
            item_AVG.setIcon(0, self.logo)
            self.message.show_message('Team logo successfully added!')


        #self.league_view_WL.setColumnCount(2)
        item_WL.setTextAlignment(0, Qt.AlignCenter)
        item_WL.setTextAlignment(1, Qt.AlignCenter)

        #item AVG 
        item_AVG.setTextAlignment(0, Qt.AlignCenter)
        item_AVG.setTextAlignment(1, Qt.AlignCenter)
        ###print("item:", item)

        # add to team WL view
        self.league_view_WL.insertTopLevelItem(0, item_WL)
        #add to team AVG view 
        self.league_view_AVG.insertTopLevelItem(0, item_AVG)
        self.clear_all()
        self.logo = None
        #self.refresh_leaderboard(vals, self.league_view_AVG, self.leaderboard_AVG)
        ###print(self.league)

        # test get all team objs in league 
        all_teams = self.league.get_all_objs()
        #print(all_teams)

    def button_upload_handler(self):
        #print("upload")
        #print(f'file dir-new team: {self.file_dir}')
        # open window to select file 
        # set a file path to file selected 
        # call Icon method to create icon 
        # set team icon to icon object 
        # set icon to stat and update dialogs ? 
        self.logo = None 
        self.file_path = None
        dialog = FileDialog(self.message, parent=self, flag='save')
        dialog.open_file_dialog()
        self.file_path = dialog.get_file_path()
        #print('file_path team_img:', file_path)
        icon, file_path = self.get_icon(self.file_path)
        self.logo = icon
            
    def get_icon(self, file_path):
        icon = Icon(file_path)
        ret_icon = icon.create_icon()
        return ret_icon, file_path
    
    def update_logo_path(self, team):
        team.logo = self.file_path 
        #print('no team logo assigned')
        
    def insert_end_avg(self, find_team):
        count = self.lv_teams.tree2_bottom.topLevelItemCount()
        team = find_team.name 
        avg = find_team.get_bat_avg()
        item = QTreeWidgetItem([team, str(avg)])
        self.lv_teams.tree2_bottom.insertTopLevelItem(count, item)
    
    
    def retranslateUi(self, AddTeam):
        AddTeam.setWindowTitle(QCoreApplication.translate("AddTeam", u"Form", None))
        #self.label.setText(QCoreApplication.translate("AddTeam", u"New Team", None))
        self.button_submit.setText(QCoreApplication.translate("AddTeam", u"Submit", None))
        self.label_2.setText(QCoreApplication.translate("AddTeam", u"Name:", None))
        self.label_3.setText(QCoreApplication.translate("AddTeam", u"Max Roster:", None))
        self.label_4.setText(QCoreApplication.translate("AddTeam", u"Logo:", None))
        self.label_5.setText(QCoreApplication.translate("AddTeam", u"Manager:", None))
        self.button_upload.setText(QCoreApplication.translate("AddTeam", u"Upload", None))
    # retranslateUi

