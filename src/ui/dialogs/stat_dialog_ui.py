# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stat_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale, 
    QMetaObject, QObject, QPoint, QRect, 
    QSize, QTime, QUrl, Qt, Slot)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter, QStandardItemModel,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QMainWindow, QApplication, QLabel, QDialog, QListView, QSizePolicy, QSpacerItem, QTreeView,
    QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QPushButton, QVBoxLayout, QHBoxLayout)
#from stat_mg_py6.demo.demo_donut_graph import MainSlice, DonutBreakdownChart
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice
from src.ui.styles.stylesheets import StyleSheets
from src.visualization.donut_graph import MainSlice, DonutBreakdownChart
from src.visualization.bar_graph import BarGraph
from src.core.player import Player, SamplePlayer
from src.core.team import Team
from src.ui.dialogs.bar_graph_dialog import BarGraphDialog
from src.visualization.graph_window import GraphWindow
from decimal import getcontext, Decimal
from src.utils.image import Icon
import random
import sys

class Ui_StatDialog(QDialog):
    def __init__(self, league, message, selected, parent=None):
        """Stats dialog showing charts and trees for a selected player/team context."""
        super().__init__(parent)
        self.league = league
        self.message = message
        self.selected = selected
        self.teams_selected = []
        self.parent = parent

        self.tree_widget = QTreeWidget(self)

         # Centered label
        label_text = self.get_label()
        self.label = QLabel(label_text, self)
        self.label.setAlignment(Qt.AlignCenter)
        

        ##print('selected:', self.selected)
        self.sample_player = SamplePlayer('Sample Player', 1, 'Sample Team', 'Sample League', ['first', 'second', 'third'], message=self.message)
        
        self.setWindowTitle("Stats Viewer")
        self.resize(800, 600)  # Resize the dialog itself

        self.layout_main = QVBoxLayout(self)
        self.layout_main.addWidget(self.label)
        self.layout_main.addWidget(self.tree_widget)
        self.layout_main.setContentsMargins(20, 20, 20, 20)  # Minimal padding
        self.layout_main.setSpacing(10)  # Minimal spacing between widgets

       
        # View Graph button
        self.view_graph_btn = QPushButton("View\nGraph", self)
        self.view_graph_btn.setFixedSize(150, 75)
        self.view_graph_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        #self.view_graph_btn.setStyleSheet("margin-bottom: 10px;")  # Optional: fine-tune padding
        self.view_graph_btn.setCursor(Qt.PointingHandCursor)
        self.view_graph_btn.clicked.connect(self.get_graph)

        # Tree widget
        #self.tree_widget = QTreeWidget(self)
        self.tree_widget.setObjectName("treeWidget")
        self.tree_widget.setColumnCount(2)
        self.tree_widget.setHeaderLabels(["Stat", "Value"])
        self.tree_widget.header().setDefaultAlignment(Qt.AlignCenter)
        self.tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tree_widget.setMinimumHeight(400)  # Optional: ensures it's not too small


        # Optional: Add vertical spacer to center content if needed
        self.layout_main.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Center the button horizontally
        self.layout_main.addWidget(self.view_graph_btn, alignment=Qt.AlignHCenter | Qt.AlignBottom)

                                # ------------------------------------------------------------------------------ #

        self.graph_window = GraphWindow(self, 'Stats Graph')
            
                                # ------------------------------------------------------------------------------ #

    def set_context(self, val):
      c = getcontext().prec = val
      return c

    def isLen(self, x, y):
        return len(str(x)) > y

    def get_dec(self, x, val):
        c = self.set_context(val)
        dec = Decimal(x) / 1
        flag = self.isLen(dec, 4)
        if not flag:
            return dec 
        return round(dec, 3)
    
    def get_rand_dec_lst(self, val):
        c = self.set_context(val)
        ret = []
        while len(ret) < 5:
            rand = random.random()
            dec = Decimal(rand) / 1
            flag = self.isLen(dec, 4)
            if not flag:
                ret.append(dec) 
            ret.append(round(dec, 3))
        return ret
        
    def get_label(self):
        if self.selected is None:
            return "League Stats"
        elif len(self.selected) == 2:
            team, num = self.selected
            return f"{team} Stats"
        else:
            player, team, num = self.selected
            return f"{player} Stats"
        
    # setup graph
    def get_graph_data(self):
        bar_graph_data = self.league.get_team_objs_barset()
        
        print('bar graph data:', bar_graph_data)

        return bar_graph_data
    
    def get_graph_data_spec(self, lst):
        bar_graph_data = self.league.get_team_objs_barset_spec(lst)
        
        #print('bar graph data:', bar_graph_data)

        return bar_graph_data
    
    def get_graph(self):
        #self.graph_window = GraphWindow('Stats Graph')

        flag = self.check_league()
        #print('get graph flag:', flag)
        match flag:
            case 'sample league':
                self.message.show_message("No teams in league.\nSample league bar graph.", btns_flag=False, timeout_ms=2000)
                self.get_sample_league()
            case 'league':
                self.get_curr_league()
            case 'sample team':
                self.message.show_message("Must update player hits, walks, and so.\nSample team bar graph.", btns_flag=False, timeout_ms=2000)
                self.get_sample_team() 
            case 'team':
                self.get_curr_graph() 
            case 'sample player' | 'player':
                #self.message.show_message("Must update player at bats, hits, and walks.\nSample player graph.")
                self.get_donut()
    
    def get_player_flag(self):
        player, team, num = self.selected
                
        find_team = self.league.find_team(team)
        find_player = find_team.get_player(player)

        self.data_player = find_player.graph_view_format_player()[0]
        flag = find_player.graph_view_format_player()[1] 

        if flag == True:
            return 'player'
        elif flag == False:
            self.message.show_message("Must update: hits, so, and walks\nSample Player Graph", btns_flag=False, timeout_ms=2000)
            return 'sample player'
    
    def get_donut(self):
        player, team, num = self.selected
                
        find_team = self.league.find_team(team)
        find_player = find_team.get_player(player)

        self.data_player = find_player.graph_view_format_player()[0]
        flag = find_player.graph_view_format_player()[1]

        #self.view_graph_btn.clicked.connect(lambda: self.get_graph(flag))
        colors = [Qt.red, Qt.darkRed, Qt.green, Qt.darkGreen, Qt.blue, Qt.darkBlue, Qt.magenta, Qt.darkMagenta, Qt.cyan, Qt.darkCyan, Qt.yellow, Qt.darkYellow, Qt.gray, Qt.darkGray, Qt.lightGray]

        self.donut_breakdown = DonutBreakdownChart(self.data_player, colors)
        self.donut_breakdown.setAnimationOptions(QChart.AllAnimations)
        self.donut_breakdown.setTitle("Player Graph View")
        self.donut_breakdown.legend().setAlignment(Qt.AlignRight)
        self.donut_breakdown.pop_dict_exp('Stat', 'Amount')
        self.donut_breakdown.add_breakdowns()

        self.chart_view = QChartView(self.donut_breakdown)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumSize(700, 600)

        self.graph_window.setCentralWidget(self.chart_view)
        self.graph_window.show()

    def check_league(self):
        flag = self.get_graph_data()
        if self.selected is None:
            if self.league.get_count() == 0:
                return 'sample league' 
            elif self.league.get_count() >=1 and flag == False:
                return 'sample league' 
            elif self.league.get_count() >= 1 and flag:
                return 'league'
        elif self.selected is not None:
            if len(self.selected) == 2:
                if flag == False:
                    return 'sample team' # check if stats exists in team 
                elif flag: 
                    return 'team'
            elif len(self.selected) == 3:
                ret = self.get_player_flag() # check if stats exists in player 
                return ret
            
    def get_sample_league(self):
        teams = ['Beef Sliders', 'Blues', 'S9', 'Pelicans', 'Rougarou']
        stats = ['hits', 'so', 'runs', 'era', 'k', 'avg']
        
        r1, r2, r3, r4, r5 = self.get_rand_dec_lst(3)

        data = [
            [1,2,3,4,5, r1],
            [10,6,3,7,8, r2],
            [11,4,7,9,4, r3], 
            [12,5,9,10,22, r4], 
            [13,7,6,3,5, r5]
        ]

        self.bar_graph = BarGraph(teams, data, stats)
        #self.bar_graph.y_axis_right.setTickInterval(0.10)
        self.bar_graph.setWindowTitle('Sample League Stats')
        self.graph_window.setCentralWidget(self.bar_graph)
        self.graph_window.show()
    
    def get_sample_team(self):
        teams = ['Beef Sliders']
        stats = ['hits', 'so', 'runs', 'era', 'k', 'avg']
        
        rand = random.random()
        rand_dec = self.get_dec(rand, 3)

        data = [
            [5,6,7,8,9, rand_dec],
        ]

        self.bar_graph = BarGraph(teams, data, stats)
        #self.bar_graph.y_axis_right.setTickInterval(0.10)
        self.bar_graph.setWindowTitle('Sample Team Stats')
        self.graph_window.setCentralWidget(self.bar_graph)
        self.graph_window.show()
    
    def get_curr_league(self):
        stats = ['hits', 'so', 'runs', 'era', 'k', 'avg']
        
        self.graph_dialog = BarGraphDialog(self.league, self.selected, self.message, self.teams_selected, self)
        self.graph_dialog.exec()

        teams_selected = [x for x in self.teams_selected]
        #print('teams selected:', teams_selected) 
        if len(teams_selected) == 0:
            self.message.show_message("Must select at least on team!", btns_flag=False, timeout_ms=2000)
            return
                
        teams, data = self.get_graph_data_spec(teams_selected)
        #print('bar graph data - teams:', teams)

        teams_updated = [x for x in teams if x in teams_selected]
        #print('teams updated - selected:', teams_updated)
        
        self.bar_graph = BarGraph(teams_updated, data, stats)
        #self.bar_graph.y_axis_right.setTickInterval(0.10)
        self.graph_window.setCentralWidget(self.bar_graph)
        self.graph_window.show()
    
    def set_context(self, val):
        c = getcontext().prec = val
        return c

    def isLen(self, x, y):
        return len(str(x)) > y

    def get_dec(self, x, val):
        c = self.set_context(val)
        dec = Decimal(x) / 1
        flag = self.isLen(dec, 4)
        if not flag:
            return dec 
        return round(dec, 3)

    def get_curr_graph(self):
        stats = ['hits', 'so', 'runs', 'era', 'k', 'avg']
        team, num = self.selected 

        find_team = self.league.find_team(team) 
                    
        hits = int(find_team.get_team_hits())
        so = int(find_team.get_team_so())
        runs = int(find_team.get_team_runs())
        era = float(find_team.get_team_era())
        k = int(find_team.get_team_k())
        #avg = "{:.3f}".format(float(find_team.get_bat_avg()))
        avg = self.get_dec(find_team.get_bat_avg(), 3)
        #print('one team avg:', avg)
        data = [
            [hits, so, runs, era, k, avg]
        ]

        self.bar_graph = BarGraph([team], data, stats)
        #self.bar_graph.y_axis_right.setTickInterval(0.10)
        self.graph_window.setCentralWidget(self.bar_graph) 
        self.graph_window.show()

    # deprecated - not in use
    def populate_stats(self, selected):
        #print('selected', selected)
        item = None
        if selected is None:
            return
        elif len(selected) == 2:
            team, avg = selected 
            item = QTreeWidgetItem([team, avg])
        elif len(selected) == 3:
            player, team, avg = selected 
            item = QTreeWidgetItem([player, avg])
        self.tree_widget.insertTopLevelItem(0, item)  

    def get_stats(self, selected):
        item = None 
        team = None 
        avg = None 
        player = None 
        ret = []
        #print('selected item:', selected)

        if selected is None:
            ##print('none selected')
            league = self.league.return_admin()
            ##print(league)
            for el in league:
                stat = el[0]
                val = el[1]
                item = QTreeWidgetItem([stat, val])
                self.tree_widget.addTopLevelItem(item)

        elif len(selected) == 2:
            team, avg = selected 
            find_team = self.league.find_team(team)
            print('team stat ui - search:', find_team)
            
            # experimental - team era 
            team_era = self.league.get_team_era()
            ##print('team era', team_era)

            logo_path = find_team.logo 
            print(logo_path, "team")
            if logo_path:
                item = QTreeWidgetItem(['Logo', ''])
                item.setTextAlignment(0, Qt.AlignCenter)
                icon = self.get_icon(logo_path)
                # Only set icon if it was successfully created
                if icon is not None:
                    item.setIcon(1, icon)
                    self.tree_widget.setIconSize(QSize(50, 50))
                self.tree_widget.addTopLevelItem(item)
            
            ###print('find team:\n', find_team)
            team_stats = find_team.return_stats()
            for el in team_stats:
                stat = el[0]
                val = el[1]
                item = QTreeWidgetItem([stat, val]) 
                item.setTextAlignment(0, Qt.AlignCenter)
                item.setTextAlignment(1, Qt.AlignCenter)
                self.tree_widget.addTopLevelItem(item)

        elif len(self.selected) == 3:
            player, team, avg = self.selected 
            find_team = self.league.find_team(team)
            find_player = find_team.get_player(player)
            image_path = find_player.image
            #print('find player', find_player)
            print(image_path, "player")
            if image_path:
                item = QTreeWidgetItem(['Photo', ''])
                item.setTextAlignment(0, Qt.AlignCenter)
                icon = self.get_icon(image_path)
                # Only set icon if it was successfully created
                if icon is not None:
                    item.setIcon(1, icon)
                    self.tree_widget.setIconSize(QSize(50, 50))
                self.tree_widget.addTopLevelItem(item)
            ###print('find player:\n', find_player)
            ret_raw = find_player.__str__().split("\n")
            ###print('ret raw:',ret_raw)
            for el in ret_raw:
                ###print('el:', el)
                temp = el.split(": ")
                stat = temp[0]
                val = temp[1]
                ###print("temp:", temp)
                ###print("stat - val:", stat, val)
                item = QTreeWidgetItem([stat, val])
                item.setTextAlignment(0, Qt.AlignCenter)
                item.setTextAlignment(1, Qt.AlignCenter)
                self.tree_widget.addTopLevelItem(item) 
                temp = None
            ##print("player:", ret)

    def get_icon(self, file_path):
        icon = Icon(file_path)
        ret_icon = icon.create_icon()
        return ret_icon
    


        
    

