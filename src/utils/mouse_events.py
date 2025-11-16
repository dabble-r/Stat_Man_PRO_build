from PySide6.QtCore import Qt, QEvent, QPoint, QObject
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QHoverEvent 


class MyHoverWidget(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.HoverEnter:
            self.handle_hover_enter(obj, event)
            return False  # Allow event to continue propagating
        elif event.type() == QEvent.Type.HoverLeave:
            self.handle_hover_leave(obj, event)
            return False
        elif event.type() == QEvent.Type.HoverMove:
            self.handle_hover_move(obj, event)
            return False
        return False  # Let other events pass through
    
    def handle_hover_enter(self, obj: QObject, event: QHoverEvent):
        # get the widget at the cursor position
        if isinstance(obj, QWidget):
            # Get child widget at local position
            child = obj.childAt(event.pos())
            if child:
                print(f"Child at: {child.objectName() or child.__class__.__name__}")
                print(f"Cursor at: {obj.objectName() or obj.__class__.__name__}")
            else:
                print(f"No child found at hover position. Widget: {obj.objectName() or obj.__class__.__name__}")
        else:
            print(f"Hover enter on non-widget: {obj.__class__.__name__}")

    def handle_hover_leave(self, obj: QObject, event: QHoverEvent):
        if isinstance(obj, QWidget):
            print(f"Mouse left at: {event.pos().x()}, {event.pos().y()}")
            print(f"Cursor left: {obj.objectName() or obj.__class__.__name__}")
        # Perform actions when mouse leaves the widget

    def handle_hover_move(self, obj: QObject, event: QHoverEvent):
        # print(f"Mouse moved within at: {event.pos().x()}, {event.pos().y()}")
        # Perform actions when mouse moves within the widget
        pass # Often, continuous move events are not needed for simple hover effects
