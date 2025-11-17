# save_csv_app.py
import sys
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QMessageBox, QDialog, QLabel, QLineEdit, QHBoxLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt
from src.data.save.save_manager import Save

# --- Custom dialog to ask for folder name -----------------------------------
class FolderNameDialog(QDialog):
    def __init__(self, base_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save CSV - Choose folder name")
        self.base_path = base_path

        layout = QVBoxLayout(self)

        base_label = QLabel(f"Base directory: {str(self.base_path)}")
        base_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(base_label)

        input_layout = QHBoxLayout()
        label = QLabel("Folder name:")
        self.line_edit = QLineEdit()
        input_layout.addWidget(label)
        input_layout.addWidget(self.line_edit)
        layout.addLayout(input_layout)

        # Buttons: OK, Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def accept(self) -> None:
        folder_name = self.line_edit.text().strip()
        if not folder_name:
            QMessageBox.warning(self, "Folder name required", "You must enter a folder name.")
            return
        # optionally sanitize folder name here
        super().accept()

    def folder_name(self) -> str:
        return self.line_edit.text().strip()

# --- The main handler that performs the save logic --------------------------
class SaveCSVHandler:
    def __init__(self, league, message, parent_widget: QWidget, db_path: Path = None, csv_path: Path = None):
        from src.utils.path_resolver import get_database_path, get_data_path
        
        self.parent = parent_widget
        # Use path resolver for database and CSV paths (works in both dev and bundled mode)
        if db_path is None:
            db_path = get_data_path("database")  # Gets data/database directory
        if csv_path is None:
            csv_path = get_data_path("exports")  # Gets data/exports directory
        
        self.db_path = db_path
        self.csv_path = csv_path
        self.league = league
        self.message = message
        
        # Construct proper paths: full database file path
        db_file_path = get_database_path()  # Uses path resolver: data/database/League.db
        # Base directory is the data directory (for file_dir)
        base_dir = get_data_path("")  # Gets data/ directory
        
        # if no League.db exists, init new db
        self.save_csv = Save(db_file_path, league, self.message, str(base_dir), ['csv', 'database'])
    
    def run(self):
        try:
            # Ensure base directory exists
            # base dir: data/exports
            self.csv_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.parent, "Filesystem error",
                                 f"Could not create base data/exports directory:\n{e}")
            return
        
        # Show folder name dialog
        dlg = FolderNameDialog(self.csv_path, parent=self.parent)
        if dlg.exec() != QDialog.Accepted:
            return  # user cancelled

        chosen_name = dlg.folder_name()
        target_folder = self.csv_path / chosen_name

        if target_folder.exists():
            choice = QMessageBox.question(
                self.parent,
                "Folder exists",
                (f"The folder '{chosen_name}' already exists in '{self.csv_path}'.\n\n"
                 "Do you want to overwrite it (delete all CSVs and save new files) or create a new folder?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            # Interpret: Yes -> Overwrite, No -> Create new, Cancel -> abort
            if choice == QMessageBox.StandardButton.Cancel:
                return
            elif choice == QMessageBox.StandardButton.Yes:
                # Overwrite flow
                try:
                    self._clear_csvs_in_folder(target_folder)
                    
                except Exception as e:
                    QMessageBox.critical(self.parent, "Error clearing folder",
                                         f"Could not clear CSV files in folder:\n{e}")
                    return
                final_folder = target_folder
            else:
                # Create new -> add timestamp
                ts = self.get_timestamp()
                final_folder = self.csv_path / f"_{chosen_name}{ts}"
                if final_folder.exists():
                  ts = self.get_timestamp(flag=True)
                  final_folder = self.csv_path / f"_{chosen_name}{ts}"
        else:
            final_folder = target_folder

        try:
            final_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.parent, "Filesystem error",
                                 f"Could not create folder '{final_folder}':\n{e}")
            return

        # Export DB tables to CSVs inside final_folder
        try:
            print("Export CSV files!")
            # Pass the full database file path, not just the directory
            db_file_path = self.db_path / "League.db"
            print(f"SaveCSVHandler - Calling save_master with db: {db_file_path}, csv: {final_folder}")
            self.save_csv.save_master(db_file_path, final_folder)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in SaveCSVHandler.run():\n{error_details}")
            QMessageBox.critical(self.parent, "Export error",
                                 f"An error occurred while exporting CSVs:\n{e}\n\n{error_details}")
            return

        QMessageBox.information(self.parent, "Export complete",
                                f"Exported CSV file(s) to:\n{final_folder}")

    def _clear_csvs_in_folder(self, folder: Path):
        if not folder.exists() or not folder.is_dir():
            return
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() == ".csv":
                p.unlink()
    
    def get_timestamp(self, flag=False):
      now = datetime.now()
      date = now.strftime("_%m%d%Y")
      if flag: 
        date = now.strftime("_%m%d%Y_%S")
      #print(f"Formatted date: {date}")
      return date