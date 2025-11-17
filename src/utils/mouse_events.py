from PySide6.QtCore import Qt, QEvent, QPoint, QObject, Signal, QTimer
from PySide6.QtWidgets import QWidget, QApplication, QDialog
from PySide6.QtGui import QHoverEvent, QMouseEvent, QCursor 

# --------------------------------------------------

class MyHoverWidget(QObject):
    # Define signals
    item_hovered = Signal(list)    # Emits the item data when hovering over an item
    hover_ended = Signal()          # Emits when mouse leaves a tree widget or popup
    
    def __init__(self, tree1_top, tree2_top, tree1_bottom, tree2_bottom, stat_popup=None, parent=None):
        super().__init__(parent)
        self.tree_widgets = [tree1_top, tree2_top, tree1_bottom, tree2_bottom]
        self.stat_popup = stat_popup  # Reference to stat snapshot popup dialog
        self.stat_widget_show = False 
        self.instance = None
        # Timer for delayed hover signal emission (1000ms delay)
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)  # Fire only once
        self.hover_timer.timeout.connect(self._emit_hover_signal)
        self.pending_instance = None  # Store instance data while waiting for timer
        self.current_tree = None  # Track which tree widget we're currently hovering over 

    # --------------------------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # Handle mouse clicks - hide popup if clicking outside
        if event.type() == QEvent.Type.MouseButtonPress:
            self.handle_mouse_click(obj, event)
            return False  # Allow event to continue propagating
        
        # Handle hover events on tree widgets only
        if event.type() == QEvent.Type.HoverEnter:
            # Check if it's one of our tree widgets
            for tree in self.tree_widgets:
                if obj == tree or obj == tree.viewport():
                    self.handle_hover_enter_tree(obj, event)
                    return False
            return False  # Allow event to continue propagating
        
        elif event.type() == QEvent.Type.HoverLeave:
            # Check if it's one of our tree widgets
            for tree in self.tree_widgets:
                if obj == tree or obj == tree.viewport():
                    self.handle_hover_leave_tree(obj, event)
                    return False
            return False
        
        elif event.type() == QEvent.Type.HoverMove:
            self.handle_hover_move(obj, event)
            return False
        
        return False  # Let other events pass through
    
    # --------------------------------------------------
    # Helper Methods
    # --------------------------------------------------
    
    def _is_click_inside_popup(self, global_pos: QPoint) -> bool:
        """Check if the click position is inside the popup dialog."""
        if not self.stat_popup or not self.stat_popup.isVisible():
            return False
        
        popup_geometry = self.stat_popup.frameGeometry()
        return popup_geometry.contains(global_pos)
    
    def _is_child_of_popup(self, obj: QObject) -> bool:
        """Check if the object is a child widget of the stat popup."""
        if not self.stat_popup:
            return False
        
        # If obj is the popup itself, return True
        if obj == self.stat_popup:
            return True
        
        # For widgets, use parentWidget() to traverse the widget hierarchy
        if isinstance(obj, QWidget):
            parent = obj.parentWidget()
            while parent is not None:
                if parent == self.stat_popup:
                    return True
                parent = parent.parentWidget()
        else:
            # For non-widget QObjects, use parent() method
            parent = obj.parent()
            while parent is not None:
                if parent == self.stat_popup:
                    return True
                # Check if parent has parent() method before calling
                if hasattr(parent, 'parent'):
                    parent = parent.parent()
                else:
                    break
        return False
    
    # --------------------------------------------------
    
    def _get_item_instance(self, tree, pos):
        """Extract item instance data from tree at given position."""
        item = tree.itemAt(pos)
        if item:
            if item.text(2) != '': 
                return [item.text(0), item.text(1), item.text(2)]
            else:
                return [item.text(0), item.text(1)]
        return None
    
    # --------------------------------------------------
    
    def _start_hover_timer_for_item(self, tree, instance):
        """Start the hover timer for a given item instance."""
        print(f"Item detected: {instance}")
        self.instance = instance
        self.pending_instance = instance
        self.current_tree = tree
        
        # Stop any existing hover timer
        if self.hover_timer.isActive():
            self.hover_timer.stop()
        
        # Start timer for 1000ms before emitting signal
        self.hover_timer.start(1500)
        print(f"Started hover timer (1000ms) for item: {instance}")
    
    # --------------------------------------------------
    # Event Handlers
    # --------------------------------------------------
    
    def handle_hover_enter_tree(self, obj: QObject, event: QHoverEvent):
        """Handle mouse entering a tree widget - start 1000ms timer to show popup."""
        for tree in self.tree_widgets:
            if obj == tree or obj == tree.viewport():
                # Map coordinates to viewport space if event came from tree widget
                # itemAt() expects viewport coordinates (excludes header)
                if obj == tree:
                    # Map from tree coordinates to viewport coordinates
                    pos = tree.viewport().mapFrom(tree, event.pos())
                else:
                    # Already in viewport coordinates
                    pos = event.pos()
                
                instance = self._get_item_instance(tree, pos)
                if instance:
                    self._start_hover_timer_for_item(tree, instance)
                else:
                    # Moved to empty space within tree - hide stats
                    # Cancel any pending hover timer
                    if self.hover_timer.isActive():
                        self.hover_timer.stop()
                        self.pending_instance = None
                    
                    if self.stat_widget_show:
                        self.stat_widget_show = False
                        self.hover_ended.emit()
                        print("Moved to empty space in tree")
                break
    
    # --------------------------------------------------
    
    def _emit_hover_signal(self):
        """Called when hover timer expires - emit the signal with pending instance."""
        if self.pending_instance is not None:
            print(f"Hover timer expired, emitting signal for: {self.pending_instance}")
            self.stat_widget_show = True
            self.item_hovered.emit(self.pending_instance)
    
    # --------------------------------------------------
    
    def handle_hover_leave_tree(self, obj: QObject, event: QHoverEvent):
        """Handle mouse leaving a tree widget - only cancel timer if not moving to another item (item 1 & 5)."""
        for tree in self.tree_widgets:
            if obj == tree or obj == tree.viewport():
                # Item 5: Check if mouse is still over a valid item before canceling
                try:
                    # Use QCursor.pos() to get global cursor position
                    cursor_pos = QCursor.pos()
                except Exception as e:
                    print(f"Error getting cursor position: {e}")
                    # Fallback: cancel timer if we can't determine position
                    if self.hover_timer.isActive():
                        self.hover_timer.stop()
                        self.pending_instance = None
                        self.current_tree = None
                    return
                
                # Check if cursor is still over this tree widget
                tree_global_rect = tree.mapToGlobal(tree.rect().topLeft())
                tree_rect = tree.rect()
                tree_rect.moveTopLeft(tree_global_rect)
                
                if tree_rect.contains(cursor_pos):
                    # Still over the tree - check if over a valid item
                    # Map from tree coordinates to viewport coordinates for itemAt()
                    tree_local_pos = tree.mapFromGlobal(cursor_pos)
                    viewport_pos = tree.viewport().mapFrom(tree, tree_local_pos)
                    item = tree.itemAt(viewport_pos)
                    if item:
                        # Still over a valid item - don't cancel timer (item 1: moving to another item)
                        print(f"Mouse still over item in tree - keeping timer: {tree.objectName()}")
                        return
                
                # Check if moving to another tree widget
                for other_tree in self.tree_widgets:
                    if other_tree != tree:
                        other_tree_global_rect = other_tree.mapToGlobal(other_tree.rect().topLeft())
                        other_tree_rect = other_tree.rect()
                        other_tree_rect.moveTopLeft(other_tree_global_rect)
                        if other_tree_rect.contains(cursor_pos):
                            # Moving to another tree - cancel timer
                            if self.hover_timer.isActive():
                                self.hover_timer.stop()
                                self.pending_instance = None
                                self.current_tree = None
                                print(f"Moving to another tree widget - canceling timer: {tree.objectName()}")
                            return
                
                # Actually leaving all tree widgets - cancel timer
                if self.hover_timer.isActive() and self.current_tree == tree:
                    self.hover_timer.stop()
                    self.pending_instance = None
                    self.current_tree = None
                    print(f"Canceled hover timer - mouse left tree widget: {tree.objectName()}")
                else:
                    self.current_tree = None
                # Note: Don't hide popup here - it will hide on click outside
                break
    
    # --------------------------------------------------
    
    def handle_mouse_click(self, obj: QObject, event: QMouseEvent):
        """Handle mouse clicks - hide popup if clicking outside the dialog."""
        if not self.stat_widget_show or not self.stat_popup or not self.stat_popup.isVisible():
            return
        
        # Get global position of the click
        global_pos = None
        if isinstance(obj, QWidget):
            global_pos = obj.mapToGlobal(event.pos())
        elif hasattr(event, 'globalPos'):
            global_pos = event.globalPos()
        elif hasattr(event, 'globalPosition'):
            # PySide6 uses globalPosition() which returns QPointF
            pos_f = event.globalPosition()
            global_pos = QPoint(int(pos_f.x()), int(pos_f.y()))
        else:
            # Fallback: use QCursor to get global position
            try:
                global_pos = QCursor.pos()
            except Exception as e:
                print(f"Error getting cursor position in click handler: {e}")
                global_pos = None
        
        if global_pos is None:
            return
        
        # Check if click is inside the popup or on a child of popup
        is_inside = self._is_click_inside_popup(global_pos) or self._is_child_of_popup(obj)
        
        if not is_inside:
            print("Mouse clicked outside popup - hiding dialog")
            self.stat_widget_show = False
            self.hover_ended.emit()
    
    # --------------------------------------------------
    
    def handle_hover_move(self, obj: QObject, event: QHoverEvent):
        """Handle mouse move within tree widgets - detect item changes and restart timer (item 2)."""
        # Check if it's one of our tree widgets
        for tree in self.tree_widgets:
            if obj == tree or obj == tree.viewport():
                # Map coordinates to viewport space if event came from tree widget
                # itemAt() expects viewport coordinates (excludes header)
                if obj == tree:
                    # Map from tree coordinates to viewport coordinates
                    pos = tree.viewport().mapFrom(tree, event.pos())
                else:
                    # Already in viewport coordinates
                    pos = event.pos()
                
                instance = self._get_item_instance(tree, pos)
                
                if instance:
                    # Check if this is a different item than the pending one (compare by value)
                    if self.pending_instance is None or self.pending_instance != instance:
                        # Item changed - restart timer with new item
                        print(f"Item changed during hover move: {instance}")
                        self._start_hover_timer_for_item(tree, instance)
                    # If same item, timer continues running - don't do anything
                # Don't cancel timer on empty space in hover_move - let HoverLeave handle that
                # This prevents false positives when moving between items
                break
