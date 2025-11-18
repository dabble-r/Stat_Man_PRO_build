from PySide6.QtWidgets import QWidget, QDialog, QCheckBox, QPushButton, QVBoxLayout, QButtonGroup, QHBoxLayout
from PySide6.QtCore import Qt




class BarGraphDialog(QDialog):
    def __init__(self, league, selected, message, styles, teams, parent):
        """Dialog to choose teams via checkboxes and trigger a bar graph render."""
        super().__init__(parent)
        self.league = league
        self.selected = selected
        self.styles = styles
        #self.setStyleSheet(self.styles.get_monochrome_style())
        self.teams_selected = teams
        self.parent = parent
        self.message = message
        self.setWindowTitle("Update Offense")
        self.resize(400, 300)
        self.max_check = 5
        
        # button layout 
        self.button_layout = QVBoxLayout()

        # ----- Submit Button -----
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(100)
        self.submit_button.clicked.connect(self.get_team_selection)
        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)

                            # -----------------------------------------------------------------------------------------------------# 

        # Right side: Radio Buttons in a group
        self.checkbox_group = QButtonGroup(self)
        self.checkboxes = []

        self.check_buttons_layout = QVBoxLayout()
        self.check_buttons_layout.setAlignment(Qt.AlignTop)

        # Container widget for the radio buttons (optional)
        self.checkbox_widget = QWidget()
        self.checkbox_setup()
        self.checkbox_widget.setLayout(self.check_buttons_layout)
       
                                # ---------------------------------------------------------------------------------------------------------------------#
                                                                # stat UI and widget setup #

                                # ---------------------------------------------------------------------------------------------------------------------#

        # Horizontal layout: form on the left, radios on the right
        content_layout = QHBoxLayout()
        content_layout.addStretch()
        content_layout.addWidget(self.checkbox_widget)
        content_layout.addLayout(self.button_layout, stretch=5)
        

         # ----- Main Layout -----
        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addSpacing(20)
        main_layout.addStretch()

        self.setLayout(main_layout)
    
    def checkbox_setup(self):
      """Populate checkbox list from current league team names and wire selection."""
      options = ["default"]

      options = [x for x in self.league.get_all_team_names()]

      for team in options:
        checkbox = QCheckBox(team)
        checkbox.stateChanged.connect(self.check_on_change)
        self.checkboxes.append(checkbox)
        self.check_buttons_layout.addWidget(checkbox)
        
    def get_team_selection(self):
      """Collect checked team names and notify parent view for graph generation."""
      # checkbox selection 
      #for el in self.teams_selected: 
          #self.parent.teams_selected.append(el)
      #print('teams selected - submit')
      if len(self.teams_selected) == 0:
          self.message.show_message("Select at least one team.", btns_flag=False, timeout_ms=2000)
      else:
        self.close()
        
    def check_on_change(self):
      for el in self.checkboxes:
        team = el.text()
        if el.isChecked():
          if team not in self.teams_selected:
            if len(self.teams_selected) < self.max_check:
              self.teams_selected.append(team)
            else:
              self.message.show_message("Limit five teams per graph.", btns_flag=False, timeout_ms=2000)
              el.setChecked(False)
              #self.teams_selected.remove(team)
              #self.parent.teams_selected.remove(team)
          if team not in self.parent.teams_selected: 
              if len(self.parent.teams_selected) < self.max_check:
                self.parent.teams_selected.append(team)
              
        else:
            # Optional: remove if unchecked
            if team in self.teams_selected:
              self.teams_selected.remove(team)
            if team in self.parent.teams_selected:
              self.parent.teams_selected.remove(team)
        
      #print('parent-teams selected:', self.parent.teams_selected)
        


      
    
      
