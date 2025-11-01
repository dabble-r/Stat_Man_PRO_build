from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from file_dialog import FileDialog, OpenFile 
from image import Image, Icon, PixMap
import sys


class ImageWindow(QMainWindow):
  def __init__(self, img):
    super().__init__()
    self.setWindowTitle("Image Viewer")
    self.img = img 
    self.scaled_pixmap = None
    pix_map_test = QPixmap("Files/beef_logo_bw.png")
    icon_test = QIcon(pix_map_test)
    pm_class = pix_map_test.__class__
    icon_class = icon_test.__class__
    
    # Central widget and layout
    central_widget = QWidget()
    #central_widget.setGeometry(100, 100, 100, 100)

    main_layout = QVBoxLayout(central_widget)

    self.img_label = QLabel()

    self.img_layout = QVBoxLayout()

    if self.img.__class__ == pm_class:
      self.scaled_pixmap = self.img.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
      self.img_label.setPixmap(self.scaled_pixmap)
      self.img_label.setScaledContents(True)
      main_layout.addWidget(self.img_label)

    elif self.img.__class__ == icon_class:
       self.setWindowIcon(self.img)
       
    self.setCentralWidget(central_widget)

    self.setGeometry(100,100,100,100)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    open_file = OpenFile()
    file_path = open_file.get_file_path()
    #image = Image(file_path)

    icon = Icon(file_path)
    pix_map = PixMap(file_path)

    icon_obj = icon.create_icon()
    pm_obj = pix_map.create_pm()


    window = ImageWindow(pm_obj)
    window.setGeometry(100, 100, 100, 100)
    window.show()
    sys.exit(app.exec())