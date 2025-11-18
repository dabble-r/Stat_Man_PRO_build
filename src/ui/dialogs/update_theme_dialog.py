from PySide6.QtWidgets import QWidget, QDialog, QPushButton, QVBoxLayout, QRadioButton, QButtonGroup, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt



class UpdateTheme(QDialog):
    def __init__(self, styles, message, parent=None):
        """Dialog to switch application theme by selecting a stylesheet variant."""
        super().__init__(parent)
        self.styles = styles
        self.message = message
        self.parent = parent
        self.setObjectName("Update Theme")

        form_layout = QVBoxLayout()

        form_widget = QWidget()
        form_widget.setLayout(form_layout)
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Right side: Radio Buttons in a group
        self.radio_group = QButtonGroup(self)
        self.radio_buttons = []

        self.radio_buttons_layout = QVBoxLayout()
        self.radio_buttons_layout.setAlignment(Qt.AlignTop)

        self.radio_btns_setup()
        
        # Container widget for the radio buttons (optional)
        self.radio_buttons_widget = QWidget()
        self.radio_buttons_widget.setLayout(self.radio_buttons_layout)

                            # ----------------------------------------------------------------------------------------------------- # 
        # button layout 
        self.button_layout = QVBoxLayout()

        # ----- Submit Button -----
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(125)
        self.submit_button.clicked.connect(self.get_theme)

        self.button_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)

                            # ----------------------------------------------------------------------------------------------------- #
        
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

        self.setLayout(main_layout)
    
    def radio_btns_setup(self):
      """Populate radio group with available theme names derived from styles object."""
      options = ["default"]
      options = [self.format_theme(style) for style in dir(self.styles) if "styles" in style]

      for i in range(len(options)):
          radio = QRadioButton(f"{options[i]}")
          if i == 0:
            radio.setChecked(True)
          self.radio_group.addButton(radio, i)
          self.radio_buttons.append(radio)
          self.radio_buttons_layout.addWidget(radio)

    def format_theme(self, str):
      """Humanize internal style attribute name (snake_case_styles) for display."""
      str = str.replace("_", " ")
      str = str[0].upper() + str[1:len(str)-7]
      lst = [el[0].upper() + el[1:] for el in str.split(" ")]
      return " ".join(lst)
    
    def no_format_theme(self, str):
      """Convert display label back to internal style attribute name."""
      str = str.lower()
      str = str.replace(" ", "_") + "_styles"
      return str
    
    def get_theme(self):
      """Apply selected theme to main window and enable dependent controls on parent."""
      selection = self.radio_group.checkedButton()
      selectionFormat = self.no_format_theme(selection.text())
      
      mainWindow = self.get_ancestor("Main Window")
      #print(mainWindow)
      mainWindow.setStyleSheet(getattr(self.styles, selectionFormat))
      ## debug
      self.parent.user_input.setEnabled(True)
      self.parent.date_combo.setEnabled(True)
      self.parent.date_combo.setCurrentIndex(0)
      self.close()
         
    def get_ancestry(self, widget):
      """Return ancestor chain for widget by following parentWidget links, avoiding loops."""
      ancestry = []
      visited = set()
      current = widget

      while current is not None and id(current) not in visited:
          ancestry.append(current)
          visited.add(id(current))
          current = current.parentWidget()
      return ancestry

    def get_ancestor(self, str):
      """Find ancestor widget by objectName, returning the first match or None."""
      ancestors = self.get_ancestry(self)
      #print(ancestors)
      for el in ancestors:
        #print(el.objectName())
        objName = el.objectName()
        if objName == str:
          return el
      return None
       
