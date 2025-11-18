from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Qt

class GraphWindow(QMainWindow):
  def __init__(self, parent, title):
    super().__init__(parent)
    self.parent = parent
    self.title = title
    self.resize(1500, 750)
    self.setWindowTitle(self.title)
    self.setWindowModality(Qt.NonModal)
    self.setWindowFlags(
        Qt.Window |
        Qt.WindowStaysOnTopHint|
        Qt.CustomizeWindowHint |
        Qt.WindowCloseButtonHint
    )
    self.setAttribute(Qt.WA_TranslucentBackground)