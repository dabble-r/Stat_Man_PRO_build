import sys 
import os
from src.ui.views.league_view_players import LeagueViewPlayers
from src.ui.views.league_view_teams import LeagueViewTeams
from src.ui.dialogs.add_save_ui import Ui_Add_Save
from src.ui.views.selection import Selection
from src.utils.tree_event_filter import TreeEventFilter
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QPushButton, QDialog, QGroupBox, QButtonGroup, QMessageBox, QMainWindow, QSizeGrip
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QTimer, QUrl, Qt)
from PySide6.QtGui import QIntValidator, QCloseEvent
from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog
from src.ui.dialogs.update_dialog_ui import UpdateDialog
from src.ui.dialogs.update_league import UpdateLeagueDialog
from src.core.linked_list import LinkedList
from src.ui.dialogs.remove import RemoveDialog
from src.utils.refresh import Refresh
from src.ui.styles.stylesheets import StyleSheets
from src.core.stack import Stack
from src.utils.undo import Undo
from src.ui.dialogs.message import Message
from src.ui.dialogs.close import CloseDialog
from src.utils.file_dialog import FileDialog

class MainWindow(QWidget):
    def __init__(self, app):
        """Main application window wiring league, views, dialogs, and event filters."""
        super().__init__()
        self.selected = None
        self.league = LinkedList()
        self.styles = StyleSheets()
        self.stack = Stack()
        self.app = app
        
        
        self.undo = Undo(self.stack, self.league)
        #self.file_dir = None
        self.message = Message(self.styles, parent=self)
        self.setStyleSheet(self.styles.light_styles)
        self.theme = None
        
        self.title = "Welcome to the league"
        self.setWindowTitle(self.title)
        self.setObjectName("Main Window") 
         
         # ---------------------------------------- install wizard setup ----------------------------------- #

        #self.exec_wizard() 
        #dir_path = self.wizard.get_selected_path()
        self.file_dialog = FileDialog(self.message, self)
        self.file_dir = self.file_dialog.get_file_dir()

        self.league_view_teams = LeagueViewTeams(self.league, self.styles, self.stack, self.file_dir, self.message, parent=self)
        self.league_view_players = LeagueViewPlayers(self.league_view_teams, self.selected, self.league, self.styles, self.undo, self.file_dir, self.message, parent=self)

        self.leaderboard = self.league_view_players.leaderboard

        # refresh main view after removal from league view
        # restores all league items to main view
        self.refresh = Refresh(self.league, self.league_view_teams, self.league_view_players, self.leaderboard)

        self.tree_widgets = [self.league_view_players.tree1_top, self.league_view_players.tree2_top, self.league_view_teams.tree1_bottom, self.league_view_teams.tree2_bottom]
        self.event_filter = TreeEventFilter(self.tree_widgets, self)
        self.set_event_filter()

                                                # ------------------------------------------------------------------ # 

        # button group box - all buttons
        self.button_group_bottom = QGroupBox('Modify', self)
        #self.button_group_bottom.setGeometry(QRect(1,1,50,75))

        # list buttons 
        self.buttons_bottom = []
        self.v_layout_buttons_bottom = QVBoxLayout()

         # ------------------------------------------------------------- #

        # Stat button to the right of second tree widget at the bottom
        self.btn_stat = QPushButton("Stat")
        self.btn_stat.clicked.connect(lambda: self.get_item(self.setup_stat_ui))
        self.v_layout_buttons_bottom.addWidget(self.btn_stat)
        self.buttons_bottom.append(self.btn_stat)
        #self.button_group_bottom.addButton(self.btn_stat)

        #self.stat_ui = Ui_StatDialog(self.league, self.message, self.selected, self)
        self.stat_widget = QDialog(self)
        self.stat_layout = QVBoxLayout(self.stat_widget)
        #self.stat_widget.setStyleSheet(self.styles.main_styles)
        
         # ------------------------------------------------------------- #
        
        # update button to the right of the second tree widget at the bottom
        self.btn_update = QPushButton("Update")
        self.v_layout_buttons_bottom.addWidget(self.btn_update)
        self.buttons_bottom.append(self.btn_update)
        #self.button_group_bottom.addButton(self.btn_update)
        self.btn_update.clicked.connect(lambda: self.get_item(self.setup_update_ui))

         # ------------------------------------------------------------- #

        # remove button to the right of the second tree widget at the bottom
        self.btn_remove = QPushButton("Remove")
        self.v_layout_buttons_bottom.addWidget(self.btn_remove)
        self.buttons_bottom.append(self.btn_remove)
        self.btn_remove.clicked.connect(lambda: self.get_item(self.setup_remove_ui))

         # ------------------------------------------------------------- #

        # refresh button to the right of the second tree widget at the bottom
        self.btn_refresh = QPushButton("Refresh")
        self.v_layout_buttons_bottom.addWidget(self.btn_refresh)
        self.buttons_bottom.append(self.btn_refresh)
        #self.button_group_bottom.addButton(self.btn_refresh)
        self.btn_refresh.clicked.connect(self.on_refresh_button_clicked)

         # ------------------------------------------------------------- #

        # buttons

        self.button_group_bottom.setLayout(self.v_layout_buttons_bottom)

        self.main_button_layout = QVBoxLayout()

        self.main_button_layout.addWidget(self.league_view_players.button_group)
        self.main_button_layout.addWidget(self.button_group_bottom)

         # -------------------------------------------------------------- # 

        self.main_lv_layout = QVBoxLayout()

        self.main_lv_layout.addLayout(self.league_view_players.top_layout)
        self.main_lv_layout.addLayout(self.league_view_teams.bottom_layout)

         # -------------------------------------------------------------- #

        self.main_h_layout = QHBoxLayout()

        self.main_h_layout.addLayout(self.main_lv_layout)
        self.main_h_layout.addLayout(self.main_button_layout)

        self.setLayout(self.main_h_layout) 


        # setup league basics on program start
        self.showMaximized()

        self.league_dialog = UpdateLeagueDialog(self.league, self.selected, self.message, self.leaderboard, self.league_view_teams, self.stack, self.undo, self.styles, parent=self)
        self.pos_center(self.league_dialog)
        #self.app.processEvents()

        self.setup_league_ui()

        self.title = f"Welcome to {self.league.admin['Name']}" if self.league.admin['Name'] else "Welcome to the league"
        self.setWindowTitle(self.title)

        # ----------------------------------------------------------------------------- #

    def closeEvent(self, event=QCloseEvent):
        reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Are you sure you want to quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

        if reply == QMessageBox.StandardButton.Yes:
            # Clear database on close - database doesn't persist between sessions
            self._clear_database_on_close()
            event.accept()
            
        if reply == QMessageBox.StandardButton.No:
            event.ignore()
            self.show()
            #self.show()
    
    def _clear_database_on_close(self):
        """Clear all data from database on application close"""
        from pathlib import Path
        import sqlite3
        from src.utils.path_resolver import get_database_path
        
        db_path = get_database_path()
        
        if not db_path.exists():
            print("No database to clear on close.")
            return
        
        try:
            print(f"Clearing database on close: {db_path}")
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            # Drop all tables
            for table in tables:
                table_name = table[0]
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                print(f"  Dropped table: {table_name}")
            
            conn.commit()
            conn.close()
            print("Database cleared on close.")
            
        except Exception as e:
            print(f"Error clearing database on close: {e}")

    def set_event_filter(self):
        for tree in self.tree_widgets:
            tree.viewport().installEventFilter(self.event_filter)
            tree.setSelectionMode(QTreeWidget.SingleSelection)
    
    def selected_is_none(self):
        locs = [self.league_view_players.tree1_top, self.league_view_players.tree2_top, self.league_view_teams.tree1_bottom, self.league_view_teams.tree2_bottom]
        ret = None
        curr = None
        for el in locs:
            curr = el.currentItem()
            if curr: 
                return (curr, el)
        return None
    
    def get_item(self, func):
        locs = [self.league_view_players.tree1_top, self.league_view_players.tree2_top, self.league_view_teams.tree1_bottom, self.league_view_teams.tree2_bottom]
        name = None
        team = None 
        avg = None
        
        selection_result = self.selected_is_none()
        print(f"get_item called with function: {func.__name__}")
        print(f"selected_is_none() returned: {selection_result}")
        
        if not self.selected_is_none():
            ##print('league')
            ##print('func:', func.__name__)
            func_name = func.__name__
            
            if func_name == 'setup_update_ui':
                # When nothing is selected, Update button shows league settings
                self.setup_league_ui()

            elif func_name == 'setup_stat_ui':
                # When nothing is selected, Stat button should show a warning
                QMessageBox.warning(self, "No Selection", "Please select a team or player to view stats.")
                return
            
            elif func_name == 'setup_remove_ui':
                # When nothing is selected, Remove button should show a warning
                QMessageBox.warning(self, "No Selection", "Please select a team or player to remove.")
                return
            
        elif self.selected_is_none():
            curr = self.selected_is_none()[0]
            obj_name = self.selected_is_none()[1].objectName()
            # ##print('obj name:', obj_name)
            
            if "top" in obj_name:
                name = curr.text(0)
                team = curr.text(1)
                avg = curr.text(2)
                self.selected = [name, team, avg]
            else:
                team = curr.text(0)
                avg = curr.text(1)
                ###print('avg', avg, len(avg))
                if len(avg) > 5:
                    avg = avg[8:-1]
                self.selected = [team, avg]
            ###print(self.selected)
            #self.setup_stat_ui()
            func()
        ##print("nothing selected")
    
    def setup_stat_ui(self):
        print("Stat button clicked")
        print(f"Selected item: {self.selected}")
        if not self.selected or len(self.selected) == 0:
            QMessageBox.warning(self, "No Selection", "Please select a team or player to view stats.")
            return
        
        self.stat_ui = Ui_StatDialog(self.league, self.message, self.selected, self.styles, parent=self.stat_widget)
        self.stat_ui.get_stats(self.selected)
        self.stat_ui.exec()
        print("Stat dialog closed")
        
        #self.stat_widget.setWindowTitle(f"Stats")
        #self.stat_widget.setModal(True)

        #self.stat_layout = QVBoxLayout()
        #self.stat_layout.addWidget(self.stat_ui)

        #self.stat_widget.setLayout(self.stat_layout)
        #self.stat_ui.populate_stats(self.selected)
        
        #self.stat_widget.show()
    
    def setup_update_ui(self):
        ##print("view update")
        dialog = UpdateDialog(self.league, self.selected, self.leaderboard, self.league_view_teams, self.stack, self.undo, self.file_dir, self.styles, self.message, parent=self)
        dialog.exec()
    
    def setup_remove_ui(self):
        print("Remove button clicked")
        print(f"Selected item: {self.selected}")
        if not self.selected or len(self.selected) == 0:
            QMessageBox.warning(self, "No Selection", "Please select a team or player to remove.")
            return
        dialog = RemoveDialog(self.league, self.selected, self.leaderboard, self.league_view_teams, self.league_view_players, parent=self)
        dialog.exec()
        print("Remove dialog closed")
    
    def setup_league_ui(self):
        #dialog = UpdateLeagueDialog(self.league, self.selected, self.message, self.leaderboard, self.league_view_teams, self.stack, self.undo, self.styles, parent=self)
        # Get screen geometry and center point
        #dialog.show()
        #self.app.processEvents()
        #self.pos_center(dialog)
        #QTimer.singleShot(0, lambda: self.pos_center(dialog))
        self.league_dialog.exec()

    def on_refresh_button_clicked(self):
        """Handler for when the user clicks the Refresh button"""
        print("Refresh button clicked by user")
        print(f"LinkedList.COUNT (class var): {LinkedList.COUNT}")
        if LinkedList.COUNT == 0:
            QMessageBox.information(self, "No Data", "There are no teams or players to refresh. Please load data first.")
            return
        self.refresh_view()
    
    def refresh_view(self):
        """Refresh the GUI views - can be called by button or programmatically"""
        print(f"Refreshing views (LinkedList.COUNT: {LinkedList.COUNT})")
        self.refresh.restore_all()
        print("Refresh completed")

    def pos_center(self, dialog):
        screen = self.app.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_center = screen_geometry.center()

        # Calculate top-left point to move the dialog
        dialog_geometry = dialog.frameGeometry()
        dialog_geometry.moveCenter(screen_center)

        # Move the dialog to the calculated position
        dialog.move(dialog_geometry.topLeft())
    