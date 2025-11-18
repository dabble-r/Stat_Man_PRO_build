from PySide6.QtWidgets import QDialog
from src.ui.styles.stylesheets import StyleSheets

class UpdateGameDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        """Skeleton dialog for future per-game updates (opponent, date, lineup, score)."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.message = message
        self.parent = parent
        
        self.setWindowTitle("New Game")
        self.resize(400, 300)
        self.styles = StyleSheets()
        #self.setStyleSheet(self.styles.main_styles)

        
        #self.show()

        
        
        '''# Widgets
        # player input - lineup
        self.input_label = QLabel("Enter Opponent:")
        self.input_label.setAlignment(Qt.AlignCenter)
        self.game_input = QLineEdit()
        self.game_input.setAlignment(Qt.AlignCenter)

        # ----- Submit Button ----- #
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.update_stats)

        # ----- Undo Button ------
        self.undo_button = QPushButton("Undo")
        self.undo_button.setFixedWidth(100)
        self.undo_button.clicked.connect(self.undo_stat)

        self.button_layout = QHBoxLayout()

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.undo_button, alignment=Qt.AlignCenter)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.input_label)
        form_layout.addWidget(self.game_input)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
'''
                            # -----------------------------------------------------------------------------------------------------# 

        '''
        # Right side: Radio Buttons in a group
        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []

        options = ["default"]

        options = ["Opponent", "Season", "Date", "Score" "Lineup"]

        radio_buttons_layout = QVBoxLayout()
        radio_buttons_layout.setAlignment(Qt.AlignTop)

        for i in range(len(options)):
            radio = QRadioButton(f"{options[i]}")
            radio.toggled.connect(self.render_input_form)
            self.radio_group.addButton(radio, i)
            self.radio_buttons.append(radio)
            radio_buttons_layout.addWidget(radio)

        # Container widget for the radio buttons (optional)
        radio_buttons_widget = QWidget()

        self.custom_order_input = QLineEdit()
        self.custom_order_input.setAlignment(Qt.AlignCenter)
        self.custom_order_input.setFixedWidth(35)
        self.custom_order_input.hide()
        radio_buttons_layout.addWidget(self.custom_order_input)

        radio_buttons_widget.setLayout(radio_buttons_layout)
        
        '''                                # ---------------------------------------------------------------------------------------------------------------------#

        '''
      # Horizontal layout: form on the left, radios on the right
        content_layout = QHBoxLayout()
        content_layout.addStretch()
        content_layout.addWidget(form_widget)
        content_layout.addSpacing(40)  # spacing between form and radios
        content_layout.addWidget(radio_buttons_widget)
        content_layout.addStretch()
      '''
        ''' # ----- Main Layout ----- #
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(self.button_layout)
        main_layout.addStretch()'''

        #self.setLayout(main_layout)
        

    def get_team_bat_order(self):
        """Return selected batting order label or None if none selected."""
        # radio button selection 
        selection = self.radio_group.checkedButton()
        if selection is None:
            return
        return selection.text()    

    def render_input_form(self):
        """Toggle custom order input visibility based on radio selection."""
        text = self.radio_group.checkedButton().text()
        if text == 'custom':
            self.custom_order_input.show()
        else:
            self.custom_order_input.hide()

    def set_lineup_team(self, order, player, team):
        """Apply lineup slot selection to team via team.set_lineup mapping."""
        '''"1-Leadoff", "Second", "3-Three Hole", "4-Cleanup", "5", "6", "7", "8", "9"'''
        match order:
            case 'Leadoff':
                team.set_lineup('lineup', '1', player, self)
            case '2':
                team.set_lineup('lineup', '2', player, self)
            case 'Three Hole':
                team.set_lineup('lineup', '3', player, self)
            case 'Cleanup':
                team.set_lineup('lineup', '4', player, self)
            case '5':
                team.set_lineup('lineup', '5', player, self)
            case '6':
                team.set_lineup('lineup', '6', player, self)
            case '7':
                team.set_lineup('lineup', '7', player, self)
            case '8':
                team.set_lineup('lineup', '8', player, self)
            case '9':
                team.set_lineup('lineup', '9', player, self)
            case "custom":
                cusom_input = self.custom_order_input.text()
                team.set_lineup('lineup', cusom_input, player, self)
    
    def check_custom_input(self, input, team):
        find_team = self.league.find_team(team)
        if input <= 9 or input > find_team.get_max_roster():
            raise ValueError("Must enter a number greater than 9 and less than or equal to team max roster.")

    def reformat_order(self, stat):
        match stat:
            case 'Leadoff':
                return '1'
            case 'Three Hole':
                return '3'
            case 'Cleanup':
                return '4'
            case _:
                return str(stat)

    def update_stats(self):
        order = self.get_team_bat_order()
        custom_input = None
        player = self.player_input.text()
        team, avg = self.selected
        find_team = self.league.find_team(team)

        if not order or not player:
            #QMessageBox.warning(self, "Input Error", "Enter player name and select batting order.")
            self.message.show_message("Enter player name and select batting order.", btns_flag=False, timeout_ms=2000)
            return 
        
        if order == 'custom':
          try:
            custom_input = self.custom_order_input.text()

            if int(custom_input) > 9 and int(custom_input) <= find_team.get_max_roster():
                ###print('team before:', find_team)

                # stack add node 
                # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
                self.stack.add_node(find_team, team, 'lineup', (custom_input, find_team.lineup[custom_input]), self.set_lineup_team, 'team')

                self.set_lineup_team(order, player, find_team)

                ###print('team after:', find_team)

            else:
                max_roster = find_team.get_max_roster()
                #QMessageBox.warning(self, "Input Error", f"Enter number between 9 and team max roster: {max_roster}.")
                self.message.show_message(f"Enter number between 9 and team max roster: {max_roster}.", btns_flag=False, timeout_ms=2000)

          except Exception as e:
              #QMessageBox.warning(self, "Input Error", f"{e}") 
              self.message.show_message(f"Inpute Error: {e}", btns_flag=False, timeout_ms=2000)

        elif order != "custom":
            ###print('team before:', find_team)

            # stack add node 
            # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
            stack_order = self.reformat_order(order)

            self.stack.add_node(find_team, team, 'lineup', (stack_order, find_team.lineup[stack_order]), self.set_lineup_team, 'team')

            self.set_lineup_team(order, player, find_team)

            ###print('team after:', find_team)
        
    def undo_stat(self):
        self.undo.undo_exp()
            
            
            

       



        