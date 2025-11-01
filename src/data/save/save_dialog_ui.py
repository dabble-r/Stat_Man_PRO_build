from PySide6.QtWidgets import QDialog, QPushButton, QCheckBox, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import QMetaObject
from src.data.save.save import Save 
import math 
import random
import os


'''class Ui_SaveDialog:
    def __init__(self, league, message, file_dir, parent: QDialog):
        self.league = league
        self.message = message
        self.file_dir = file_dir
        self.parent = parent
        self.rand = random.randint(1, 1000)
        self.db = f"{self.file_dir}/DB/{self.league.name}.db" if self.league.name else f'{self.file_dir}/DB/db_{self.rand}.db'
        self.setupUi(parent)

    def setupUi(self, SaveDialog: QDialog):
        SaveDialog.setObjectName("SaveDialog")
        SaveDialog.resize(400, 300)

        # Layout
        if SaveDialog.layout() is None:
            self.layout = QVBoxLayout(SaveDialog)
        else:
            self.layout = SaveDialog.layout()

        # Label
        self.label = QLabel(SaveDialog)
        self.label.setObjectName("label")
        self.layout.addWidget(self.label)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.button_ok = QPushButton("OK", SaveDialog)
        self.button_ok.setObjectName("button_ok")
        self.button_ok.clicked.connect(self.button_ok_handler)

        self.button_cancel = QPushButton("Cancel", SaveDialog)
        self.button_cancel.setObjectName("button_cancel")
        self.button_cancel.clicked.connect(self.button_cancel_handler)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.button_ok)
        self.button_layout.addWidget(self.button_cancel)
        self.layout.addLayout(self.button_layout)

        self.retranslateUi(SaveDialog)
        QMetaObject.connectSlotsByName(SaveDialog)

    def retranslateUi(self, SaveDialog):
        SaveDialog.setWindowTitle("Save Progress")
        self.label.setText("Do you want to save your progress?")

    def button_ok_handler(self):
        print(f"Saving progress for league: {self.league.admin['Name']}")

        if self.league.admin['Name'] == 'League':
            self.message.show_message(f"Please update league name:\n '{self.league.admin['Name']}' before saving!")
            return
       
        save = Save(self.db, self.league, self.message, self.file_dir)
        save.save_master(self.db, f"{self.file_dir}/CSV", "master_export.csv")

        self.parent.accept()
        
    def button_cancel_handler(self):
        print("Save canceled.")
        self.parent.reject()
    '''




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
            self.message.show_message("Please select at least one save option.")
            return

        # Return selected items
        self.selection = ",".join(selections)
        print(f"User selected save option(s): {self.selection}")

        if self.league.admin['Name'] == 'League':
            self.message.show_message(f"Please update league name:\n '{self.league.admin['Name']}' before saving!")
            return
       
        save = Save(self.db, self.league, self.message, self.file_dir, self.selection)
        save.save_master(self.db, f"{self.file_dir}/CSV")

        self.accept()

    def button_cancel_handler(self):
        print("Save canceled.")
        self.selection = "cancel"
        self.reject()
