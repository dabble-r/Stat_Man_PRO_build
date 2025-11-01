# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'leaderboard.ui'
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
from PySide6.QtWidgets import (QApplication, QLabel, QListWidget, QListWidgetItem,
    QSizePolicy, QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView)
from bisect import insort_left, bisect_left

class Leaderboard(QWidget, object):
    def __init__(self, tree_widget, league, parent=None):
        super().__init__()
        self.leaderboard_list = []
        self.league = league
        self.parent = parent

        self.tree_widget = tree_widget
        self.tree_widget.setColumnCount(3)
        self.tree_widget.header().setDefaultAlignment(Qt.AlignCenter)
        self.tree_widget.setHeaderLabels(["Player", "Team", "AVG"])

        header1 = self.tree_widget.header()
        header1.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
    ''' # setupUi
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(400, 300)
        self.tree_widget = QTreeWidget(Form)
        self.tree_widget.setColumnCount(3)
        self.tree_widget.header().setDefaultAlignment(Qt.AlignCenter)
        self.tree_widget.setHeaderLabels(["Player", "Team", "AVG"])
        
        self.tree_widget.setObjectName(u"tree_widget")
        self.tree_widget.setGeometry(QRect(30, 80, 350, 200))
        self.label = QLabel(Form)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(160, 30, 81, 16))

        """self.label_2 = QLabel(Form)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(70, 60, 49, 16))
        self.label_3 = QLabel(Form)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(180, 60, 49, 16))
        self.label_4 = QLabel(Form)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(310, 60, 49, 16))"""

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    '''

    # refresh for new player
    def refresh_leaderboard(self, new_player): # new player type -> tuple or list
        ###print('new player:', new_player)
        args = self.get_args(new_player)
        self.add_leaderboard_list(args)
        ###print("leaderboard:", self.leaderboard_list)
        self.sort_leaderboard()
        self.insert_widget()
    
    # refresh for player removal
    def refresh_leaderboard_removal(self, target): # new player type -> tuple or list
        self.remove_leaderboard_item_name(target)
        ###print("leaderboard:", self.leaderboard_list)
        self.sort_leaderboard()
        self.insert_widget()
    
    def get_args(self, new_player):
        name = number = team = positions = avg = None
        if type(new_player) == list or type(new_player) == tuple:
            name, number, team, positions, avg = new_player
            return (name, number, team.name, positions, avg)
        else:
            name = new_player.name 
            number = new_player.number 
            team = new_player.team
            positions = new_player.positions 
            avg = new_player.AVG
            # ensure team is a string name for display
            team_name = team.name if hasattr(team, 'name') else team
            return (name, number, team_name, positions, avg)

    def add_leaderboard_list(self, args):
        name, number, team, positions, avg = args
        self.remove_dup(args)
        self.leaderboard_list.append((name, team, str(avg)))
        print('leaderboard - team name:', name, team, avg)

    def sort_leaderboard(self):
        self.leaderboard_list.sort(key=self.my_sort)
        return self.leaderboard_list
        
    def my_sort(self, x):
        return float(x[2])
    
    def remove_dup(self, args):
        name, number, team, positions, avg = args
        for indx, el in enumerate(self.leaderboard_list):
            if el[0] == name:
                self.leaderboard_list.pop(indx)
    
    def insert_widget(self):
        ###print(self.leaderboard_list, type(self.leaderboard_list))
        self.tree_widget.clear()
        for el in self.leaderboard_list:
            ###print("list el:", el)
            item = QTreeWidgetItem([el[0], el[1], str(el[2])])
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            self.tree_widget.insertTopLevelItem(0, item)
    
    def remove_handler(self, target):
        self.remove_widget_item(target)
        self.remove_leaderboard_item(target)
    
    def remove_widget_item(self, target):
        count = self.tree_widget.topLevelItemCount()
        player = target.name
        i = 0 
        while i < count:
            item = self.tree_widget.topLevelItem(i)
            name = item.text(0)
            if name == player:
                self.tree_widget.takeTopLevelItem(i)
                return
            i += 1
    
    # player instance
    def remove_leaderboard_item(self, target):
        player = target.name
        for indx, el in enumerate(self.leaderboard_list):
            if el[0] == player:
                self.leaderboard_list.pop(indx)
    
    # player name
    def remove_leaderboard_item_name(self, target):
        name = target.name
        for indx, el in enumerate(self.leaderboard_list):
            if el[0] == name:
                ##print(el[0], name)
                self.leaderboard_list.pop(indx)
    
    def restore_items(self):
        players = self.league.get_all_players_avg() # name only
        print('players:', players)

        for el in players:
            temp = el[0]
            if temp not in [x[0] for x in self.leaderboard_list]: # name only 
                name = el[0]
                team = el[1].name
                avg = el[2]
                self.leaderboard_list.append((name, team, avg))
        self.sort_leaderboard()
        self.insert_widget()



            





