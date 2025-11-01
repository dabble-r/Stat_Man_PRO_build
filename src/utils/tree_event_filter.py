from PySide6.QtCore import QObject, QEvent, QModelIndex
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtWidgets import QTreeView, QTreeWidget

class TreeEventFilter_1(QObject):
    def __init__(self, trees_lst):
        """Legacy filter to enforce single selection and clear selection on whitespace."""
        super().__init__()
        self.trees = trees_lst
        self.tree_obj_names = self.get_obj_name()
    
    def set_selection_mode(self):
        """Set single-selection mode on all tracked tree widgets."""
        for tree in self.trees:
            tree.setSelectionMode(QAbstractItemView.SingleSelection)

    
    def eventFilter(self, obj, event):
        """Clear selection when clicking whitespace in any managed tree widget."""
        for tree in self.trees:
            if obj == tree.viewport():
                if event.type() == QEvent.Type.MouseButtonPress:
                    index = tree.indexAt(event.pos())
                    if not index.isValid():
                        tree.clearSelection()
                        if isinstance(tree, QTreeWidget):
                            tree.setCurrentItem(None)
                        elif isinstance(tree, QTreeView):
                            tree.setCurrentIndex(QModelIndex())
        return False
    
    def limit_one_selection(self):
        """Ensure that only one tree has a selection at any time by clearing others."""
        ##print("new selection")
        self.set_selection_mode()
        for tree in self.trees:
          selected = tree.selectedItems()
          if selected:
            temp = tree.objectName()
            to_clear = self.tree_obj_names[temp]
            ##print("temp:", temp)
            ##print("to clear:", to_clear)
            for el in to_clear:
                el.clearSelection()
                el.setCurrentItem(None)
                ##print("el:", el)
        ##print(self.tree_obj_names)

    def get_obj_name(self):
        """Build a map of tree objectName → list of other trees to clear when selected."""
        ret = {}
        for tree in self.trees:
            temp = tree.objectName()
            # create dict where key is tree widget with selected item and value is list of tree widgets to clear selection
            ret[temp] = [x for x in self.trees if x.objectName() != temp]
            temp = None
        return ret
     

class TreeEventFilter(QObject):
    def __init__(self, trees_lst, parent):
        """Current event filter to unify selection behavior across multiple trees."""
        super().__init__()
        self.trees = trees_lst
        self.parent = parent

    def eventFilter(self, obj, event):
        """Clear other trees, set selection on click, or clear all on whitespace click."""
        if event.type() == QEvent.Type.MouseButtonPress:
            for tree in self.trees:
                if obj == tree.viewport():
                    index = tree.indexAt(event.pos())

                    # Clear selection in all trees first
                    for other_tree in self.trees:
                        other_tree.clearSelection()
                        if isinstance(other_tree, QTreeWidget):
                            other_tree.setCurrentItem(None)
                        elif isinstance(other_tree, QTreeView):
                            other_tree.setCurrentIndex(QModelIndex())

                    # If clicked in whitespace, don't select anything
                    if not index.isValid():
                        self.parent.selected = None
                        return True  # Consume the event

                    # If clicked on a valid item, select it
                    if isinstance(tree, QTreeWidget):
                        item = tree.itemAt(event.pos())
                        if item:
                            tree.setCurrentItem(item)
                            item.setSelected(True)
                    elif isinstance(tree, QTreeView):
                        tree.setCurrentIndex(index)
                        tree.selectionModel().select(
                            index,
                            tree.selectionModel().SelectionFlag.ClearAndSelect
                        )
        return False
      