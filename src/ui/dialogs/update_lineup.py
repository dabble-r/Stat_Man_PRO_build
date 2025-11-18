from PySide6.QtWidgets import QWidget, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from src.ui.logic.dialogs.update_lineup_logic import (
  order_to_slot,
  apply_lineup_assignment,
  update_stats
)

# --------------------------------------------------

class UpdateLineupDialog(QDialog):
    def __init__(self, league, selected, leaderboard, lv_teams, stack, undo, message, parent=None):
        """Dialog to assign batting order slots to a named player on the team."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.leaderboard = leaderboard
        self.lv_teams = lv_teams
        self.leaderboard_AVG = []
        self.stack = stack
        self.undo = undo
        self.message = message
        
        self.setWindowTitle("Update Lineup")
        self.resize(400, 300)
        
        
        # Widgets
        # player input - lineup
        self.player_label = QLabel("Enter Player:")
        self.player_label.setAlignment(Qt.AlignCenter)
        self.player_input = QLineEdit()
        self.player_input.setAlignment(Qt.AlignCenter)

        # ----- Submit Button ----- #
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.update_stats_handler)

        # ----- Undo Button ------
        self.undo_button = QPushButton("Undo")
        self.undo_button.setFixedWidth(100)
        self.undo_button.clicked.connect(self.undo_stat)

        self.button_layout = QHBoxLayout()

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)
        self.button_layout.addWidget(self.undo_button, alignment=Qt.AlignCenter)

        form_layout = QVBoxLayout()
        form_layout.addWidget(self.player_label)
        form_layout.addWidget(self.player_input)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                            # -----------------------------------------------------------------------------------------------------# 

        # Right side: Radio Buttons in a group
        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []

        options = ["default"]

        options = ["Leadoff", "2", "Three Hole", "Cleanup", "5", "6", "7", "8", "9", "custom"]

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

                                # ---------------------------------------------------------------------------------------------------------------------#

        # Horizontal layout: form on the left, radios on the right
        content_layout = QHBoxLayout()
        content_layout.addStretch()
        content_layout.addWidget(form_widget)
        content_layout.addSpacing(40)  # spacing between form and radios
        content_layout.addWidget(radio_buttons_widget)
        content_layout.addStretch()

         # ----- Main Layout ----- #
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(self.button_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def get_team_bat_order(self):
        """Return selected lineup slot label or None if nothing selected."""
        # radio button selection 
        selection = self.radio_group.checkedButton()
        if selection is None:
            return
        return selection.text()    

    def render_input_form(self):
        """Toggle custom order input when 'custom' slot is selected."""
        text = self.radio_group.checkedButton().text()
        if text == 'custom':
            self.custom_order_input.show()
        else:
            self.custom_order_input.hide()

    def update_stats_handler(self): 
        update_stats(self.get_team_bat_order(), self.player_input.text(), self.stack, self.message, self.custom_order_input, self.league, self.selected, self._apply_lineup_ui_delegate)
    
    '''def update_stats(self):
        """Validate inputs, push undo action, and update team lineup accordingly."""
        order_label = self.get_team_bat_order()
        player = self.player_input.text()
        team, avg = self.selected
        find_team = self.league.find_team(team)

        if not order_label or not player:
            self.message.show_message("Enter player name and select batting order.", btns_flag=False, timeout_ms=2000)
            return 

        # Map order to slot and validate custom slot if needed
        custom_text = self.custom_order_input.text() if order_label == 'custom' else None
        slot = order_to_slot(order_label, custom_text)
        if order_label == 'custom':
            try:
                validate_custom_slot(slot, find_team.get_max_roster())
            except Exception as e:
                self.message.show_message(f"Inpute Error: {e}", btns_flag=False, timeout_ms=2000)
                return

        # Build undo payload and push
        undo_prev = build_undo_payload_for_lineup(find_team, slot if slot else '')
        self.stack.add_node(find_team, team, 'lineup', undo_prev, self._apply_lineup_ui_delegate, 'team')

        # Apply lineup assignment
        self._apply_lineup_ui_delegate(order_label, player, find_team)'''

    def _apply_lineup_ui_delegate(self, order_label, player, team_obj):
        """Delegate that applies lineup from order label (kept for undo compatibility)."""
        # Keep existing mapping semantics intact
        slot = order_to_slot(order_label, self.custom_order_input.text() if order_label == 'custom' else None)
        apply_lineup_assignment(team_obj, slot, player, self)
        
    def undo_stat(self):
        self.undo.undo_exp()
            
            
            

       



        