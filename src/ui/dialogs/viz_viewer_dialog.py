"""
Dialog that displays a matplotlib figure with Export image and Close.

Used after building a chart from NL Query results.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent

logger = logging.getLogger(__name__)

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    FigureCanvasQTAgg = None
    Figure = None


class VizViewerDialog(QDialog):
    """Shows a matplotlib figure with Export image and Close."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chart")
        self.setMinimumSize(700, 500)
        self._canvas = None
        self._figure: Optional[Figure] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        if not HAS_MATPLOTLIB:
            from PySide6.QtWidgets import QLabel
            layout.addWidget(QLabel("matplotlib is not installed. Install with: pip install matplotlib"))
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.reject)
            layout.addWidget(close_btn)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMinimumHeight(400)
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._scroll_widget)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        export_btn = QPushButton("Export image...")
        export_btn.clicked.connect(self._export_image)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def set_figure(self, figure: Figure):
        """Set the matplotlib figure to display. Call after showEvent or before show()."""
        if not HAS_MATPLOTLIB or figure is None:
            return
        self._figure = figure
        if self._canvas:
            self._scroll_layout.removeWidget(self._canvas)
            self._canvas.deleteLater()
        self._canvas = FigureCanvasQTAgg(figure)
        self._scroll_layout.addWidget(self._canvas)
        self._canvas.draw()

    def _export_image(self):
        if not self._figure:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export chart",
            str(Path.home()),
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if not path:
            return
        try:
            self._figure.savefig(path, bbox_inches="tight", dpi=150)
            QMessageBox.information(self, "Export", f"Saved to {path}")
        except Exception as e:
            logger.exception("Export image failed")
            QMessageBox.warning(self, "Export failed", str(e))

    def closeEvent(self, event: QCloseEvent):
        """Close the figure to avoid resource warnings."""
        if self._figure and HAS_MATPLOTLIB:
            import matplotlib.pyplot as plt
            plt.close(self._figure)
            self._figure = None
        super().closeEvent(event)
