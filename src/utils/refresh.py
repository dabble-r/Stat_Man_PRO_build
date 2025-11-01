from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QLabel, QSizePolicy, QWidget, QTreeWidget, QPushButton, QVBoxLayout, QHBoxLayout, QDialog, QHeaderView, QTreeWidgetItem)

class Refresh():
  def __init__(self, league, lv_teams, lv_players, leaderboard):
    """Helper to reconcile GUI tree views with the current league state."""
    self.lv_teams = lv_teams 
    self.lv_players = lv_players 
    self.leaderboard = leaderboard 
    self.league = league

    self.players = self.lv_players.tree1_top 
    self.players_avg = self.leaderboard.tree_widget
    self.teams_wl = self.lv_teams.tree1_bottom
    self.teams_avg = self.lv_teams.tree2_bottom

  def restore_all(self):
    """Rebuild players/teams/leaderboard views from league aggregates and stats."""
    wl = self.league.get_all_wl() 
    avg = self.league.get_all_avg()
    players_league = self.league.get_all_players_num()

    # all league players in tree widget
    players_view = [x[0] for x in self.get_widget_view(self.players, 3)] # player name only

    # all league teams in tree widget 
    # wl tree widget
    teams_view_wl = [x[0] for x in self.get_widget_view(self.teams_wl, 2)] # team name only
    # avg tree widget
    teams_view_avg = [x[0] for x in self.get_widget_view(self.teams_avg, 2)] # team name only

    # restore players view
    self.restore_view(players_league, players_view, self.players, 3)

    # restore teams wl view
    self.restore_view(wl, teams_view_wl, self.teams_wl, 2)

    # restore teams avg view
    self.restore_view(avg, teams_view_avg, self.teams_avg, 2)

    # restore leaderboard
    self.leaderboard.restore_items()
  
  def get_logo(self, team):
    """Return QIcon built from team.logo path if available; None on failure."""
    logo = None
    find_team = self.league.find_team(team)
    if find_team and find_team.logo:
      # Convert string path to QIcon for display
      from src.utils.image import Icon
      try:
        icon_obj = Icon(find_team.logo)
        logo = icon_obj.create_icon()
      except Exception as e:
        print(f"Warning: Could not load team logo from '{find_team.logo}': {e}")
        logo = None
    return logo

  def restore_view(self, lst, view, widget, num):
    """Insert missing rows into a QTreeWidget based on target list snapshot."""
    ##print('player league:', players_league)
    for el in lst: # item name only
      ##print('view el:', el)
      if el[0] not in view:
        if num == 3:
          item = QTreeWidgetItem([el[0], el[1], str(el[2])])
          item.setTextAlignment(0, Qt.AlignCenter)
          item.setTextAlignment(1, Qt.AlignCenter)
          item.setTextAlignment(2, Qt.AlignCenter)
          widget.insertTopLevelItem(0, item)
          print('refresh player:', el[0], el[1], el[2])
        elif num == 2:
          team = el[0]
          logo = self.get_logo(team)
          item = QTreeWidgetItem([el[0], str(el[2])])
          if logo:
            item.setIcon(0, logo)
            widget.setIconSize(QSize(35,35))
          item.setTextAlignment(0, Qt.AlignCenter)
          item.setTextAlignment(1, Qt.AlignCenter)
          item.setTextAlignment(2, Qt.AlignCenter)
          widget.insertTopLevelItem(0, item)
          print('refresh team:', el[0], el[1], el[2])
          

  def get_widget_view(self, tree_widget, num):
    """Return a list of row tuples read from a QTreeWidget (2 or 3 columns)."""
    ret = []
    count = tree_widget.topLevelItemCount()
    i = 0 
    while i < count:
        if num == 3:
          item = tree_widget.topLevelItem(i)
          name = item.text(0)
          team = item.text(1)
          avg = item.text(2)
          ret.append((name, team, avg))
        elif num == 2:
          item = tree_widget.topLevelItem(i)
          team = item.text(0)
          avg = item.text(1)
          ret.append((team, avg))
        i += 1
    return ret
  

