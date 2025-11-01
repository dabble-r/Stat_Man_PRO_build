from PySide6.QtWidgets import QDialog, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import QMetaObject
from src.data.load.load import load_all_from_db
from src.data.load.load_csv import load_all_csv_to_db
from src.utils.path_resolver import get_database_path
import math 
import random

class Ui_LoadDialog:
    def __init__(self, league, message, file_dir, csv_path, parent: QDialog):
        self.league = league
        self.message = message
        self.file_dir = file_dir
        self.csv_path = csv_path
        self.parent = parent
        # Use path resolver to get database path (consistent with save functionality)
        # Always use League.db in the standard location
        self.db = str(get_database_path())
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
        # Prefer CSV import to instantiate league/teams/players, then refresh UI
        from src.utils.path_resolver import get_data_path
        # Use path resolver for CSV directory (consistent with save paths)
        csv_dir = str(get_data_path("exports"))  # CSV files are typically in data/exports
        if self.db:
            load_all_csv_to_db(self.league, csv_dir, self.db, self.parent.stack, parent=self.parent)
        else:
            self.message.show_message("Database path not available. Please set a league name before loading.")
            return

        self.parent.accept()
        
    def button_cancel_handler(self):
        print("Save canceled.")
        self.parent.reject()
    