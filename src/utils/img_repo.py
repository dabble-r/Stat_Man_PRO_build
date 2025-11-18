from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QDir
import os


class CreateDir():
  def __init__(self, new_folder):
    # Define the path for the new directory
    self.new_folder = new_folder
    self.existing_directory_path = '.'
    self.new_directory = None
  
  def get_existing(self):
    directory_path = QFileDialog.getExistingDirectory(
        None, "Select Directory", "")

    if directory_path:
        #print(f"Selected directory: {directory_path}")
        self.existing_directory_path = directory_path

    else:
        print("No directory selected.")

  def create_dir(self):
    # checks for existing directory
    # if exists returns
    if self.check_exists():
      return

    # user selects directory to store images
    self.get_existing()

    full_path = os.path.join(self.existing_directory_path, self.new_folder)
    dir_creator = QDir()
    
    # Create the directory
    if not dir_creator.exists(full_path):
      new_dir = dir_creator.mkdir(full_path)
      if new_dir:
          #print(f"Directory '{full_path}' created successfully.")
          self.new_directory = full_path
      else:
          #print(f"Directory already exists '{full_path}'.")
          self.new_directory = '.'
    
  def get_new_dir(self):
     return self.new_directory
  
  def check_exists(self):
    # /mnt/c/Users/njbro/Documents/StatManager
    full_path = "/mnt/c/Users/njbro/Documents/StatManager" 
    dir = os.path.exists(full_path)
    if dir:
      self.new_directory = full_path
      return True 
    return False


    


