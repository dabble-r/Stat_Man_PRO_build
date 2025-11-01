from PySide6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem

class Selection(QWidget):
    def __init__(self, widget):
        """Helper to snapshot the currently selected item from a tree widget."""
        super().__init__()
        self.selected_item = widget.currentItem()

    def get_selected_item(self):
        """Return the stored selected item reference (may be None)."""
        #print("selected item", self.selected_item)
        return

