from PySide6.QtWidgets import QDialog, QPushButton, QCheckBox, QLabel, QVBoxLayout, QHBoxLayout
from src.data.save.save_manager import Save
import random



class SaveDialog(QDialog):
    def __init__(self, league, message, file_dir, parent=None):
        super().__init__(parent)
        self.league = league
        self.message = message
        self.file_dir = file_dir
        self.rand = random.randint(1, 1000)
        
        # Use admin['Name'] if available, otherwise league.name, otherwise generate random name
        league_name = None
        if hasattr(self.league, 'admin') and self.league.admin.get('Name'):
            league_name = self.league.admin['Name']
        elif hasattr(self.league, 'name') and self.league.name and self.league.name != 'League':
            league_name = self.league.name
        
        # Construct database path - always use League.db as the filename for consistency
        self.db = f"{self.file_dir}/DB/League.db"
        print(f"SaveDialog - Database path set to: {self.db}")
        self.selection = None  # "database", "csv", "database,csv", "cancel"

        self.setWindowTitle("Save Progress")
        self.resize(400, 200)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Label
        self.label = QLabel("Choose where you want to save your progress:", self)
        layout.addWidget(self.label)

        # Checkboxes
        self.checkbox_db = QCheckBox("Database", self)
        self.checkbox_csv = QCheckBox("CSV", self)
        layout.addWidget(self.checkbox_db)
        layout.addWidget(self.checkbox_csv)

        # Buttons
        button_layout = QHBoxLayout()
        self.button_ok = QPushButton("OK", self)
        self.button_ok.clicked.connect(self.button_ok_handler)

        self.button_cancel = QPushButton("Cancel", self)
        self.button_cancel.clicked.connect(self.button_cancel_handler)

        button_layout.addStretch()
        button_layout.addWidget(self.button_ok)
        button_layout.addWidget(self.button_cancel)
        layout.addLayout(button_layout)

    def button_ok_handler(self):
        selections = []
        if self.checkbox_db.isChecked():
            selections.append("database")
        if self.checkbox_csv.isChecked():
            selections.append("csv")

        if not selections:
            # Nothing selected -> show error
            self.message.show_message("Please select at least one save option.", btns_flag=False, timeout_ms=2000)
            return

        # Return selected items
        self.selection = ",".join(selections)
        print(f"User selected save option(s): {self.selection}")

        if self.league.admin['Name'] == 'League':
            self.message.show_message(f"Please update league name:\n '{self.league.admin['Name']}' before saving!", btns_flag=False, timeout_ms=2000)
            return
       
        save = Save(self.db, self.league, self.message, self.file_dir, self.selection)
        save.save_master(self.db, f"{self.file_dir}/CSV")

        self.accept()

    def button_cancel_handler(self):
        print("Save canceled.")
        self.selection = "cancel"
        self.reject()
