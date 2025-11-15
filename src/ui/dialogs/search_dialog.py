from PySide6.QtWidgets import QWidget, QTreeWidget, QDialog, QLabel, QLineEdit, QHeaderView, QPushButton, QMessageBox, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy, QTreeWidgetItem
from PySide6.QtGui import QIntValidator, QValidator, QRegularExpressionValidator
from PySide6.QtCore import QCoreApplication, Qt, QTimer, QRegularExpression
from src.ui.views.league_view_teams import LeagueViewTeams

from src.ui.styles.stylesheets import StyleSheets
from src.core.node import NodeStack
from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog
from typing import Union
from src.core.player import Player
from src.core.team import Team
import random


class SearchDialog(QDialog):
    def __init__(self, league, selected, stack, undo, message, parent=None):
        """Search team or player dialog; populate search results for a selected player or team."""
        super().__init__(parent)
        self.league = league
        self.selected = None
        self.type = None
        self.stack = stack
        self.undo = undo
        self.message = message
        self.setWindowTitle("Search Team or Player")
        self.resize(500, 350)
        
        # Widgets
        self.int_label = QLabel("Enter value:")
        self.int_label.setAlignment(Qt.AlignCenter)
        self.int_input = QLineEdit()
        #self.int_input.setValidator(self.string_validator())
        self.int_input.setAlignment(Qt.AlignCenter)

        # button layout 
        self.button_layout = QHBoxLayout()

        # ----- Submit Button -----
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(125)
        self.submit_button.clicked.connect(self.search_handler)

        # ----- Current View Button -----
        self.current_view_button = QPushButton("Current View")
        self.current_view_button.setFixedWidth(175)
        self.current_view_button.clicked.connect(self.curr_view_handler)

         # ----- Current View Button -----
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFixedWidth(125)
        self.clear_button.clicked.connect(self.clear_search_tree)

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.current_view_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.clear_button, alignment=Qt.AlignCenter)
        
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
                                                                # search widget - tree widget setup #
        
        self.search_tree_widget = QTreeWidget(self)
        self.search_tree_widget.setVisible(False)
        self.search_tree_widget.setObjectName("Search Results")                   
        self.search_tree_widget.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.search_tree_widget.setSelectionMode(QTreeWidget.SingleSelection)
        self.search_tree_widget.header().setDefaultAlignment(Qt.AlignCenter)
        self.search_tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
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
        main_layout.addWidget(self.search_tree_widget)
        main_layout.addStretch()

        self.setLayout(main_layout)

                        #----------------------------------------------------------------------------------------------------------------#
    def tree_widget_setup(self, selection: str):
        """Setup the search tree widget."""
        if selection == "player":
          self.search_tree_widget.setHeaderLabels(["Name", "Team", "Average"])
          self.search_tree_widget.setColumnCount(3)
          self.search_tree_widget.setColumnWidth(0, 100)
          self.search_tree_widget.setColumnWidth(1, 100)
          self.search_tree_widget.setColumnWidth(2, 100)
          
        elif selection == "team":
          self.search_tree_widget.setHeaderLabels(["Team", "Average"])
          self.search_tree_widget.setColumnCount(2)
          self.search_tree_widget.setColumnWidth(0, 100)
          self.search_tree_widget.setColumnWidth(1, 100)
        
        elif selection == "number":
          self.search_tree_widget.setHeaderLabels(["Name", "Team", "Average"])
          self.search_tree_widget.setColumnCount(3)
          self.search_tree_widget.setColumnWidth(0, 100)
          self.search_tree_widget.setColumnWidth(1, 100)
          self.search_tree_widget.setColumnWidth(2, 100)
          
        else:
          self.message.show_message("Invalid selection.", btns_flag=False, timeout_ms=2000)

    def string_validator(self) -> QRegularExpressionValidator:
        """Validate the string input."""
        regex = QRegularExpression("^[a-zA-Z]+$")
        validator = QRegularExpressionValidator(regex, self)
        return validator

    def radio_btns_setup(self):
        """Create and configure offense radio buttons for supported stat updates."""
        options = ["player", "team", "number"]

        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            if options[i] == "player":
              radio.setChecked(True)
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            self.radio_buttons_layout.addWidget(radio)

    def get_player_stat(self):
        """Return the currently selected radio stat label (as displayed)."""
        # radio button selection 
        selection = self.radio_group.checkedButton().text()
        return selection
    
    def search_handler(self):
        """Handle the search request based on the selected radio button."""
        selection = self.get_player_stat()

        if selection is None:
          self.message.show_message("Please select a search type.", btns_flag=False, timeout_ms=2000)
          return

        self.tree_widget_setup(selection)
        self.populate_search_tree(selection)

        self.int_input.clear()

    def populate_search_tree(self, selection: Union[str, int]): 
      """Populate the search tree with the search results.""" 

      if selection == "player": 
        player = self.int_input.text()
        find_player = self.league.find_player(player)
        print("find player:", find_player)

        if find_player:
          self.dups_handler(find_player.name, player=find_player)
          
        else:
          self.message.show_message("Player not found.", btns_flag=False, timeout_ms=2000)
          return

      elif selection == "team":
        team = self.int_input.text()
        find_team = self.league.find_team(team) 

        if find_team:
          self.dups_handler(find_team.name, team=find_team)

        else:
          self.message.show_message("Team not found.", btns_flag=False, timeout_ms=2000)
          return
      
      elif selection == "number": 
        try:
          number = int(self.int_input.text())
        except ValueError:
          self.message.show_message("Please enter a valid number.", btns_flag=False, timeout_ms=2000)
          return
        
        find_player_list = self.league.find_player_by_number(number)
        print("find player list:", find_player_list)

        if len(find_player_list) > 0:
          self.dups_handler(find_player_list)

        else:
          self.message.show_message("Player number not found.", btns_flag=False, timeout_ms=2000)
          return

    def curr_view_handler(self):  
      """Handle the current view request."""
      #print("Current view button clicked")
      
      if not self.get_item():
        self.message.show_message("Please select a team or player.", btns_flag=False, timeout_ms=2000)
        return

      if self.type == "player":
        self.selected = [self.selected.text(0), self.selected.text(1), self.selected.text(2)]

      elif self.type == "team":
        self.selected = [self.selected.text(0), self.selected.text(1)]

      elif self.type == "number":
        self.selected = [self.selected.text(0), self.selected.text(1), self.selected.text(2)]
       

      dialog = Ui_StatDialog(self.league, self.message, self.selected, parent=self.stat_widget)
      dialog.get_stats(self.selected)
      dialog.exec()

    def get_item(self):
      locs = [self.search_tree_widget]
      for el in locs:
          curr = el.currentItem()
          if curr: 
            self.selected = curr
            return True
      return False

    def clear_search_tree(self): 
      self.search_tree_widget.clear()
      self.search_tree_widget.setVisible(False)
      self.resize(500, 350)

    def check_dups(self, target: str) -> bool:
      for i in range(self.search_tree_widget.topLevelItemCount()):
        item = self.search_tree_widget.topLevelItem(i)
        if item.text(0) == target:
          return True
      return False
    
    def permit_dups(self, target: Union[str, list]) -> bool | None:
      if isinstance(target, str) and self.check_dups(target):
        # Explicitly show buttons for user choice
        self.message.show_message(f"Search results for {target} already found.", btns_flag=True)
        if self.message.choice == "ok": 
          return True  # User wants to add duplicate
        elif self.message.choice == "no": 
          return False  # User doesn't want to add - do nothing
        else:  # "cancel" or None
          return None  # User cancelled - clear tree
      elif isinstance(target, str) and not self.check_dups(target):
        # No duplicates found - proceed with adding
        return True

      elif isinstance(target, list):
        ret = []
        for el in target: 
          if self.check_dups(el.name):
            ret.append(el.name)
        if len(ret) > 0:
          # Explicitly show buttons for user choice
          self.message.show_message(f"Search results for\n {[x for x in ret]}]\n already found.", btns_flag=True)
          if self.message.choice == "ok": 
            return True  # User wants to add duplicates
          elif self.message.choice == "no": 
            return False  # User doesn't want to add - do nothing
          elif self.message.choice == "cancel":
            return None  # User cancelled - clear tree
        else:
          # No duplicates found in list - proceed with adding
          return True
    
    def dups_handler(self, target: Union[str, list], player: Player = None, team: Team = None): 
      ret = self.permit_dups(target)
      
      if ret == False: 
        # User selected "no" - do nothing, message already closed
        return False

      elif ret == None:
        # User selected "cancel" - clear tree and hide it
        self.search_tree_widget.clear()
        self.search_tree_widget.setVisible(False)
        self.resize(500, 350)
        return None

      elif ret == True: 
        # User selected "ok" OR no duplicates found - add item to tree
        if player:
          self.add_item_player(player)
          return
        elif team:
          self.add_item_team(team)
          return
        elif isinstance(target, list):
          self.add_item_number(target)
          return

    def add_item_player(self, player: Player):
      self.search_tree_widget.setVisible(True)
      self.resize(500, 750)
      self.type = "player"
      player_name = player.name  
      team = player.team.name
      avg = player.get_AVG()
      item = QTreeWidgetItem([player_name, team, str(avg)])
      item.setTextAlignment(0, Qt.AlignCenter)
      item.setTextAlignment(1, Qt.AlignCenter)
      item.setTextAlignment(2, Qt.AlignCenter)
      self.search_tree_widget.addTopLevelItem(item)

    def add_item_team(self, team: Team):
      self.search_tree_widget.setVisible(True)
      self.resize(500, 750)
      self.type = "team"
      name = team.name 
      avg = team.get_bat_avg()
      item = QTreeWidgetItem([name, str(avg)])
      item.setTextAlignment(0, Qt.AlignCenter)
      item.setTextAlignment(1, Qt.AlignCenter)
      self.search_tree_widget.addTopLevelItem(item)

    def add_item_number(self, player_list: list):
      self.search_tree_widget.setVisible(True)
      self.resize(500, 750)
      self.type = "number"
      for el in player_list:
        player_name = el.name  
        team = el.team.name
        avg = el.get_AVG()
        item = QTreeWidgetItem([player_name, team, str(avg)])
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setTextAlignment(1, Qt.AlignCenter)
        item.setTextAlignment(2, Qt.AlignCenter)
        self.search_tree_widget.addTopLevelItem(item)

    