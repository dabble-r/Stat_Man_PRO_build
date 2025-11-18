# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'new_player_w.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QTreeWidgetItem, QCheckBox, QButtonGroup
from src.core.player import Player, Pitcher
from src.utils.file_dialog import FileDialog
from src.utils.image import Icon

class Ui_NewPlayer(QWidget, object):
    def __init__(self, league_view, leaderboard, league, file_dir, message, parent=None):
        """Form/dialog to create a new player and assign positions, team, and image."""
        super().__init__()
        self.league_view_players = league_view
        self.leaderboard = leaderboard
        self.league = league
        self.selection_pos = []
        self.selection_team = ''
        self.image = None
        self.file_path = None
        self.file_dir = file_dir
        self.message = message
        self.parent = parent
        self.new_player_flag = False
       
    
    def setupUi(self, AddPlayer):
        """Build the New Player UI and wire handlers/validators for inputs and checks."""
        AddPlayer.setWindowTitle("New Player Form")
        AddPlayer.resize(650, 450)
        
        # Main vertical layout
        self.main_layout = QVBoxLayout(AddPlayer)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Helper function to create labeled line edit rows
        def create_input_row(label_text):
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(80)
            edit = QLineEdit()
            edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(label)
            layout.addWidget(edit)
            return layout, edit

        # Input rows
        row1, self.name = create_input_row("Name:")
        row2, self.number = create_input_row("Number:")
        #row3, self.team = create_input_row("Team:")
        #row4, self.positions = create_input_row("Positions:")
        self.number.setValidator(QIntValidator())

        # input layout - left column 
        self.left_column = QVBoxLayout()
        self.left_column.addLayout(row1)
        self.left_column.addLayout(row2)
        #self.left_column.addLayout(row3)
        #self.left_column.addLayout(row4)

        # input layout - rigth column 
        # radio buttons 
        # possible player positions 
        # Right side: Radio Buttons in a group
        self.check_pos_widget = QWidget()
        self.check_box_pos = []

        options = ["default"]

        options = ["pitcher", "catcher", "first base", "second base", "third base", "shortstop", "left field", "center field", "right field"]

        self.check_buttons_pos_layout = QVBoxLayout()
        self.check_buttons_pos_layout.setAlignment(Qt.AlignTop)

        self.check_pitcher = QCheckBox("pitcher")
        self.check_pitcher.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_pitcher)

        self.check_catcher = QCheckBox("catcher")
        self.check_catcher.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_catcher)

        self.check_first = QCheckBox("first base")
        self.check_first.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_first)

        self.check_second = QCheckBox("second base")
        self.check_second.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_second)

        self.check_third = QCheckBox("third base")
        self.check_third.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_third)

        self.check_short = QCheckBox("shortstop")
        self.check_short.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_short)

        self.check_left = QCheckBox("left field")
        self.check_left.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_left)

        self.check_center = QCheckBox("center field")
        self.check_center.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_center)

        self.check_right = QCheckBox("right field")
        self.check_right.stateChanged.connect(self.check_on_change_pos)
        self.check_box_pos.append(self.check_right)

        self.check_buttons_pos_layout.addWidget(self.check_pitcher)
        self.check_buttons_pos_layout.addWidget(self.check_catcher)
        self.check_buttons_pos_layout.addWidget(self.check_first)
        self.check_buttons_pos_layout.addWidget(self.check_second)
        self.check_buttons_pos_layout.addWidget(self.check_third)
        self.check_buttons_pos_layout.addWidget(self.check_short)
        self.check_buttons_pos_layout.addWidget(self.check_left)
        self.check_buttons_pos_layout.addWidget(self.check_center)
        self.check_buttons_pos_layout.addWidget(self.check_right)

        self.check_pos_widget.setLayout(self.check_buttons_pos_layout)

        # right column
        # select team check boxes 
        self.check_buttons_team_widget = QWidget()

        self.check_buttons_team_layout = QVBoxLayout()
        self.check_buttons_team_layout.setAlignment(Qt.AlignTop)

        self.check_buttons_team_group = QButtonGroup(self)

        options = self.league.get_all_team_names() or ['Teams']

        self.check_boxes_team = []

        for i in range(len(options)):
            check = QCheckBox(f"{options[i]}")
            
            check.stateChanged.connect(self.check_on_change_team)
            self.check_boxes_team.append(check)
            self.check_buttons_team_group.addButton(check, i)
            self.check_buttons_team_layout.addWidget(check)

        self.check_buttons_team_widget.setLayout(self.check_buttons_team_layout)
            
        # horizontal layout for input, check position buttons, and check team buttons
        self.input_layout = QHBoxLayout()
        self.input_layout.addLayout(self.left_column)
        self.input_layout.addWidget(self.check_pos_widget)
        self.input_layout.addWidget(self.check_buttons_team_widget)

        # Upload row
        upload_layout = QHBoxLayout()

        self.input_new_player = QLabel("File:")
        self.button_upload = QPushButton("Upload")

        self.button_upload.clicked.connect(self.button_upload_handler)

        upload_layout.addWidget(self.input_new_player)
        upload_layout.addWidget(self.button_upload)

        # Submit button (centered)
        self.button_submit = QPushButton("Submit")
        self.button_submit.clicked.connect(self.add_league_view)
        self.button_submit.setFixedWidth(120)

        # Header label
        self.label_new_player = QLabel("Add New Player")
        self.label_new_player.setAlignment(Qt.AlignCenter)
        #self.label_new_player.setStyleSheet("font-size: 18px; font-weight: bold;")

        # Add widgets to main layout
        self.main_layout.addWidget(self.label_new_player)
        self.main_layout.addLayout(self.input_layout)
        #self.main_layout.addLayout(row1)
        #self.main_layout.addLayout(row2)
        #self.main_layout.addLayout(row3)
        #self.main_layout.addLayout(row4)
        self.main_layout.addLayout(upload_layout)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.button_submit, alignment=Qt.AlignRight)
    
        self.retranslateUi(AddPlayer)

        QMetaObject.connectSlotsByName(AddPlayer)
    
    def get_ancestry(self, widget):
      ancestry = []
      visited = set()
      current = widget

      while current is not None and id(current) not in visited:
          ancestry.append(current)
          visited.add(id(current))
          current = current.parentWidget()

      return ancestry

    def get_ancestor(self, str):
      ancestors = self.get_ancestry(self)
      #print(ancestors)
      for el in ancestors:
        #print(el.objectName())
        objName = el.objectName()
        if objName == str:
          return el
      return None
    
    def check_on_change_team(self, state):
        self.selection_team = ''
        for el in self.check_boxes_team:
            if el.isChecked():
                ##print(el, el.text())
                team = el.text()
                self.selection_team += team
                ##print(self.selection_team)
    
    def check_on_change_pos(self):
        for el in self.check_box_pos:
            if el.isChecked():
                ##print(el, el.text())
                position = el.text()
                if position not in self.selection_pos:
                    self.selection_pos.append(position)
        ##print(self.selection_pos)
    
    def check_dups(self, player, team):
        find_team = self.league.find_team(team)
        if find_team:
            find_player = find_team.get_player(player)
            if find_player:                
                return True 
        return False
                    
    def clear_all(self):
        self.name.clear()
        self.number.clear()
        #self.team.clear()
        #self.positions.clear()
    
    def new_player_text(self):
        name = self.name.text()
        num = self.number.text()
        #team = self.team.text()
        team = self.selection_team
        #pos = [x.strip().lower() for x in self.positions.text().split(",")]
        pos = self.selection_pos
        ##print('new player text:', name, num, team, pos)
        return (name, num, team, pos)
    
    def input_check(self):
        if not self.name.text() or not self.number.text() or self.selection_team == '' or len(self.selection_pos) == 0:
            ##print('check:',self.new_player_text())
            self.message.show_message("Please enter a player name, number, team, and select at least one position.", btns_flag=False, timeout_ms=2000)
            #QMessageBox.warning(self, "Input Error", "Please enter a player name, number, team, and select at least one position.")
            return False
        
        pos = self.new_player_text()[3]
        ###print('pos:', pos)
        options = ['catcher','pitcher','first base','second base','third base','shortstop','left field','center field','right field']
        for el in pos:
            ###print('el:', el)
            if el not in options:
                self.message.show_message(f"' {el} ' not a valid player position.", btns_flag=False, timeout_ms=2000)
                #QMessageBox.warning(self, "Input Error", f"' {el} ' not a valid player position.")
                return False

    def new_player_handler(self):
        ###print("submitting...")
        if self.input_check() == False:
            return

        args_player = self.new_player_text()
        ###print('args:', args_player)
        name, num, team, pos = args_player 
        find_team = self.league.find_team(team)
        print('new player - team', find_team)

        if self.team_check(team) == False:
            #print('team not found') 
            self.new_player_flag = True
            self.message.show_message("Error: player not created!", btns_flag=False, timeout_ms=2000)
            return

        elif self.check_dups(name, team) == True:
            #print('player already exists!')
            self.new_player_flag = True
            self.message.show_message("Player already exists!", btns_flag=False, timeout_ms=2000)
            return
        
        else:
            if "pitcher" in pos:
                new_player = Pitcher(name, num, find_team, self.league, pos, message=self.message)
                #print(f'new player: {pos}') 
            else:
                new_player = Player(name, num, find_team, self.league, pos, message=self.message)
                #print(f'new player: {pos}') 
            if self.image and self.file_path:
                self.message.show_message('Player image successfully added!', btns_flag=False, timeout_ms=2000)
                new_player.image = self.file_path

            #print('new player message inst', new_player.message)
            return new_player
            
    def team_check(self, team):
        find_team = self.league.find_team(team)
        if find_team:
            return True 
        return False

    def add_league_view(self):
        ##print("submitting...")
        inst_player = self.new_player_handler()
        if self.new_player_flag == True:
            return
        ###print("inst player:", inst_player)
        if inst_player:
            # args --> name, number, team, positions
            #args_player = self.new_player_text()
            args_player = inst_player.name, inst_player.number, inst_player.team, inst_player.positions, inst_player.AVG
            ###print("args player:", args_player)

            item = QTreeWidgetItem([inst_player.name, inst_player.team.name, inst_player.number])
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            ###print("item:", item)

            self.league_view_players.insertTopLevelItem(0, item)

            # update leaderboard
            self.leaderboard.refresh_leaderboard(args_player)

            # add to linked list 
            find_team = self.league.find_team(self.selection_team)
            find_team.add_player(inst_player)
            self.clear_all()     
        else:
            print("error submitting new player")
        #self.clear_all()
    
    def button_upload_handler(self):
        #print("upload")
        # open window to select file 
        # set a file path to file selected 
        # call Icon method to create icon 
        # set team icon to icon object 
        # set icon to stat and update dialogs ? 
        self.image = None
        self.file_path = None
        dialog = FileDialog(self.message, parent=self.parent, flag='save')
        dialog.open_file_dialog()
        self.file_path = dialog.get_file_path()
        #print('file path:', file_path)
        self.get_icon(self.file_path)
    
    def get_icon(self, file_path):
        icon = Icon(file_path)
        ret_icon = icon.create_icon()
        self.image = ret_icon
    
    def update_image(self, player):
        if self.file_path:
            player.image = self.file_path
            return
        #print('no team logo assigned')

    def retranslateUi(self, AddPlayer):
        AddPlayer.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.input_new_player.setText(QCoreApplication.translate("Form", u"Image:", None))
        self.button_upload.setText(QCoreApplication.translate("Form", u"Upload", None))
        self.button_submit.setText(QCoreApplication.translate("Form", u"Submit", None))
        self.label_new_player.setText(QCoreApplication.translate("Form", u"New Player", None))
    # retranslateUi




   