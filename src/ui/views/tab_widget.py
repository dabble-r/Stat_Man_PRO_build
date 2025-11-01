from PySide6.QtWidgets import QApplication, QTabWidget, QWidget, QLabel, QVBoxLayout, QDialog

class TabWidget(QTabWidget):
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.pages = {}
        self.layouts = {}
        self.setWindowTitle(f"{self.title}")
        self.resize(500, 750)

    def create_tab(self, pg_n, layout_n, pg_title):
      # Create some content widgets for the tabs
      #setattr(self, f'{pg_n}', QWidget())
      self.pages[pg_n] = QWidget()

      layout = QVBoxLayout()
      self.pages[pg_n].setLayout(layout)

      #setattr(self, f'{layout_n}', QVBoxLayout(getattr(self, f'{pg_n}')))
      self.layouts[layout_n] = layout
      #getattr(self, f'{pg_n}')

      layout.addWidget(QLabel(pg_title))
      
      self.add_tab(pg_n, pg_title)

    def add_tab(self, pg_n, pg_title):
      # Add tabs to the QTabWidget
      page = self.pages[pg_n]
      self.addTab(page, pg_title)
    
    def enable_tabs(self):
        for i in range(self.count()):
          self.setTabEnabled(i, True)

   

        

