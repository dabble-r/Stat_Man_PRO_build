from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QDateEdit, QComboBox, QPushButton, QMessageBox, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy, QTreeWidgetItem
from PySide6.QtGui import QIntValidator, QCloseEvent
from PySide6.QtCore import QCoreApplication, Qt, QTimer, QRect, QPoint, QDate
from src.ui.views.league_view_teams import LeagueViewTeams

from src.ui.styles.stylesheets import StyleSheets
from src.ui.dialogs.update_theme_dialog import UpdateTheme
import random

class UpdateLeagueDialog(QDialog):
    def __init__(self, league, selected, message, leaderboard, lv_teams, stack, undo, styles, parent=None):
        """Dialog to update league admin fields, season dates, and theme; includes launcher."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.message = message
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.styles = styles
        self.parent = parent
        self.new_season = None
        self.new_date = None
        self.theme = None
        self.league_name = self.league.isDefaultName() 
        self.setObjectName("Update League")

        default = "League"
        self.setWindowTitle(f"Welcome to the {self.league_name if self.league_name else default}!")
        
        #self.styles = StyleSheets()
        #self.setStyleSheet(self.styles.modern_styles)
        #self.setGeometry(100, 100, 400, 300) # Initial position and size
        #self.move(200, 200) # Move to new position
        
        # Widgets
        # player input - lineup
        self.player_label = QLabel("Enter Admin:")
        self.player_label.setAlignment(Qt.AlignCenter)
        self.user_input = QLineEdit()
        self.user_input.setAlignment(Qt.AlignCenter)

        # ----- Submit Button ----- #
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(150)
        self.submit_button.clicked.connect(self.update_stats)

        # ----- Launch Button ----- #
        self.launch_button = QPushButton("Launch")
        self.launch_button.setFixedWidth(150)
        self.launch_button.clicked.connect(self.launch_league)

        # ----- Undo Button ------
        #self.undo_button = QPushButton("Undo")
        #self.undo_button.setFixedWidth(100)
        #self.undo_button.clicked.connect(self.undo_stat)

        self.button_layout = QHBoxLayout()

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.launch_button, alignment=Qt.AlignCenter)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.player_label)
        form_layout.addWidget(self.user_input)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                            # -----------------------------------------------------------------------------------------------------# 
        
        self.date_layout = QVBoxLayout()
        self.date_edit = QDateEdit(self)

        self.date_combo = QComboBox(self)
        self.date_combo.setEnabled(False)
        self.date_combo.addItems(['Select...', 'Season Start', 'Season End'])

        self.date_layout.addWidget(self.date_combo)
        self.date_layout.addWidget(self.date_edit)

        curr = QDate.currentDate()

        d = curr.day()
        m = curr.month()
        y = curr.year() - 1

        max_date = curr.addDays(365)

        self.date_edit.setDate(curr) # Set initial date to current date
        self.date_edit.setMinimumDate(QDate(y, m, d)) # Set minimum selectable date
        self.date_edit.setMaximumDate(max_date) # Set maximum selectable date
        self.date_edit.setCalendarPopup(True) # Enable calendar popup

        self.date_edit.dateChanged.connect(self.on_change_date)

        self.date_combo.activated.connect(self.on_activate_combo)
        self.date_combo.currentTextChanged.connect(self.on_text_changed)

                                    # ---------------------------------------------------------------------------------------- #

        # Right side: Radio Buttons in a group
        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []
        self.selected = None

        options = ["default"]

        options = ["Name", "Commissioner", "Historian", "Treasurer", "Recruitment", "Communications", "Theme"]

        radio_buttons_layout = QVBoxLayout()
        radio_buttons_layout.setAlignment(Qt.AlignTop)

        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")

            # league name is default 'League'
            if self.league_name is True:
                print("league name - 1: ", self.league_name)
                if options[i] == "Name":
                    #radio.setEnabled(True) 
                    radio.setChecked(True)
                else:
                    if options[i] == 'Theme':
                        radio.toggled.connect(self.on_toggle_theme)
                    radio.setEnabled(False)
                    
            # league name has been updated
            elif self.league_name is False:
                print("league name - 2: ", self.league_name)
                radio.setEnabled(True)
                self.date_combo.setEnabled(True)
                if options[i] == 'Theme':
                        radio.toggled.connect(self.on_toggle_theme)
                
                
            #radio.toggled.connect(self.on_toggle_all) 
           
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            radio_buttons_layout.addWidget(radio)

        # Container widget for the radio buttons (optional)
        self.user_input.setFocus()
        self.date_combo.setEnabled(False)
        self.date_edit.setEnabled(False)
        radio_buttons_widget = QWidget()
        radio_buttons_widget.setLayout(radio_buttons_layout)

                                # ---------------------------------------------------------------------------------------------------------------------#

        # Horizontal layout: form on the left, radios on the right
        content_layout = QHBoxLayout()
        content_layout.addStretch()
        content_layout.addWidget(form_widget)
        content_layout.addSpacing(40)  # spacing between form and radios
        content_layout.addWidget(radio_buttons_widget)
        content_layout.addLayout(self.date_layout)
        content_layout.addStretch()

         # ----- Main Layout ----- #
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(self.button_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def closeEvent(self, event: QCloseEvent): 
        if self.league_name is False:
            event.accept()

        else:
            reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Would you like to continue without customizing league?",
                QMessageBox.Ok | QMessageBox.Cancel
            )

            if reply == QMessageBox.Ok:
                event.accept()

            elif reply == QMessageBox.Cancel:
                event.ignore()
            
    def launch_league(self):
        if self.league_name is True:
            reply = QMessageBox.question(
                    self,
                    "Confirm Close",
                    "Would you like to continue without customizing league?",
                    QMessageBox.Ok | QMessageBox.Cancel
                )

            if reply == QMessageBox.Ok:
                self.destroy()

            elif reply == QMessageBox.Cancel:
                return
            
        else:
            self.destroy()
    
    def on_toggle_all(self):
        self.user_input.setEnabled(True)
        self.date_combo.setEnabled(False)
    
    def on_toggle_theme(self, checked):
        if checked:
            self.user_input.setEnabled(False)
            self.date_combo.setEnabled(False)
            self.set_theme()
        
    def on_toggle_date(self):
        self.user_input.setEnabled(False)
        self.date_combo.setEnabled(True)
    
    def set_theme(self):
        dialog = UpdateTheme(self.styles, self.message, parent=self)
        dialog.exec()
        self.user_input.setEnabled(True)
        self.date_combo.setEnabled(True)
        self.date_combo.setCurrentIndex(0)
        
    def set_checked_btn(self, str):
        for el in self.radio_buttons:
            if el.text() == str:
                el.setChecked(True)
    
    def set_uncheck_btn(self, str):
        for el in self.radio_buttons:
            if el.text() == str:
                el.setChecked(False)
                
    def get_checked_str(self, str):
        for el in self.radio_buttons:
            if el.text() == str:
                return el.isChecked() 
        return False

    def get_checked_btn(self):
        for el in self.radio_buttons:
            if el.isChecked() == True: 
                return el
        return None
    
    
    def on_submit(self):
        self.date_combo.setEnabled(True)
        self.date_combo.setCurrentIndex(0)
        for el in self.radio_buttons:
            el.setEnabled(True)
        self.league_name = self.league.admin['Name']
        self.setWindowTitle(f"Welcome to the {self.league_name}!")
        print("league name - submit:", self.league_name)
        
       
        #self.date_edit.setEnabled(True)
    
    def on_change_date(self, new_date: QDate):
        ##print('new date:', new_date)
        day = new_date.day()
        week = new_date.dayOfWeek()
        month = new_date.month()
        year = new_date.year()
        self.new_date = (day, week, month, year)
    
    def on_change_combo(self):
        self.date_combo.close()
    
    def on_activate_combo(self):
        self.clear_all()
        self.user_input.setEnabled(False)
        self.date_edit.setEnabled(True)
        
    def on_text_changed(self, text):
        season = text 
        ##print(season)
        self.new_season = season
        
    def clear_all(self):
        self.user_input.clear()
        for el in self.radio_buttons:
            el.setEnabled(True)

    def get_league_admin(self):
        # radio button selection 
        radio = self.radio_group.checkedButton().text()
        combo = self.date_combo.currentIndex()
        ##print(radio)
        ##print(combo)

        if combo == 0:
            return radio 
        elif combo != 0:
            return self.date_combo.currentText()
        else:
            return None
            
    def set_admin_league(self, stat, val):
        '''"League Name", Commissioner", "Historian", "Treasurer", "Recruitment", "Communications'''
        match stat:
            case "Name":
                print('Name:', stat, val)
                self.league.set_admin('admin', stat, val, self)
            case 'Commissioner':
                self.league.set_admin('admin', stat, val, self)
            case 'Historian':
                self.league.set_admin('admin', stat, val, self)
            case 'Treasurer':
                self.league.set_admin('admin', stat, val, self)
            case 'Recruitment':
                self.league.set_admin('admin', stat, val, self)
            case 'Communications':
                self.league.set_admin('admin', stat, val, self)
            case "Season Start":
                ##print('season')
                ##print(self.new_date)
                day, week, month, year = self.new_date
                ##print(stat)
                self.league.set_admin('admin', stat, f"{month}--{day}--{year}", self)
            case "Season End":
                ##print('season')
                ##print(self.new_date)
                day, week, month, year = self.new_date
                ##print(stat)
                self.league.set_admin('admin', stat, f"{month}--{day}--{year}", self)
            
    def update_stats(self):
        stat = self.get_league_admin()
        #print('update stat:', stat)
        val = self.user_input.text()

        if 'Season' not in stat:
            if not stat or not val:
                QMessageBox.warning(self, "Input Error", "Enter player name and select admin position.")
                return 
            
        elif 'Season' in stat:
            if self.new_date is None:
                QMessageBox.warning(self, "Input Error", "Please select date and submit.")
                return 
        ##print('league before:', self.league.get_admin())

        # stack add node 
        # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
        # self.stack.add_node(self.league, None, 'admin', (stat, self.league.admin[stat]), self.set_admin_league, 'league')

        self.set_admin_league(stat, val)

        self.on_submit()

        self.clear_all()

        ##print('league after:', self.league.get_admin())
    
    def undo_stat(self):
        self.undo.undo_exp()
          
            
            