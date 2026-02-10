"""
Dialog for choosing visualization options (chart type, columns, labels, palette).

Used by the NL Query Dialog when the user clicks Visualize on query results.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QMessageBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

CHART_TYPES = ["Bar", "Line", "Scatter", "Histogram", "Box"]
PALETTES = ["default", "viridis", "Set3", "colorblind", "pastel", "muted", "deep"]


class VizOptionsDialog(QDialog):
    """Dialog to configure chart type, column mapping, and appearance."""

    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.df = dataframe
        self.options: dict[str, Any] = {}
        self.setWindowTitle("Visualization Options")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Chart type
        chart_group = QGroupBox("Chart")
        form = QFormLayout()
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(CHART_TYPES)
        self.chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        form.addRow("Chart type:", self.chart_type_combo)
        chart_group.setLayout(form)
        layout.addWidget(chart_group)

        # Columns
        col_group = QGroupBox("Columns")
        col_form = QFormLayout()
        self.x_col_combo = QComboBox()
        self.x_col_combo.addItem("(select)", None)
        for c in self.df.columns:
            self.x_col_combo.addItem(str(c), c)
        col_form.addRow("X / category:", self.x_col_combo)

        self.y_col_combo = QComboBox()
        self.y_col_combo.addItem("(none)", None)
        for c in self.df.columns:
            self.y_col_combo.addItem(str(c), c)
        col_form.addRow("Y / value:", self.y_col_combo)

        self.series_col_combo = QComboBox()
        self.series_col_combo.addItem("(none)", None)
        for c in self.df.columns:
            self.series_col_combo.addItem(str(c), c)
        col_form.addRow("Series / group:", self.series_col_combo)

        self.group_by_combo = QComboBox()
        self.group_by_combo.addItem("(none)", None)
        for c in self.df.columns:
            self.group_by_combo.addItem(str(c), c)
        col_form.addRow("Group by (agg):", self.group_by_combo)

        self.agg_combo = QComboBox()
        self.agg_combo.addItems(["mean", "sum", "count"])
        col_form.addRow("Aggregation:", self.agg_combo)

        col_group.setLayout(col_form)
        layout.addWidget(col_group)

        # Appearance
        app_group = QGroupBox("Appearance")
        app_form = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Chart title")
        app_form.addRow("Title:", self.title_edit)
        self.x_label_edit = QLineEdit()
        self.x_label_edit.setPlaceholderText("X axis label")
        app_form.addRow("X label:", self.x_label_edit)
        self.y_label_edit = QLineEdit()
        self.y_label_edit.setPlaceholderText("Y axis label")
        app_form.addRow("Y label:", self.y_label_edit)
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(PALETTES)
        app_form.addRow("Palette:", self.palette_combo)
        app_group.setLayout(app_form)
        layout.addWidget(app_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.plot_btn = QPushButton("Plot")
        self.plot_btn.setDefault(True)
        self.plot_btn.clicked.connect(self._on_plot)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.plot_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._on_chart_type_changed(self.chart_type_combo.currentText())

    def _on_chart_type_changed(self, text: str):
        ct = (text or "").lower()
        self.y_col_combo.setEnabled(ct not in ("histogram",))
        if ct == "histogram":
            # Prefer first numeric for histogram
            numeric = list(self.df.select_dtypes(include=["number"]).columns)
            if numeric and self.x_col_combo.currentData() not in numeric:
                for i in range(self.x_col_combo.count()):
                    if self.x_col_combo.itemData(i) in numeric:
                        self.x_col_combo.setCurrentIndex(i)
                        break

    def _on_plot(self):
        chart_type = (self.chart_type_combo.currentText() or "bar").lower()
        x_col = self.x_col_combo.currentData()
        if not x_col and chart_type != "box":
            QMessageBox.warning(
                self,
                "Invalid Options",
                "Please select an X / category column."
            )
            return
        if chart_type == "histogram":
            col = x_col or (list(self.df.select_dtypes(include=["number"]).columns) or [None])[0]
            if col not in self.df.columns or not pd.api.types.is_numeric_dtype(self.df[col]):
                QMessageBox.warning(
                    self,
                    "Invalid Options",
                    "Histogram requires a numeric X column."
                )
                return
        if chart_type in ("line", "scatter") and not self.y_col_combo.currentData():
            QMessageBox.warning(
                self,
                "Invalid Options",
                "Please select a Y / value column for this chart type."
            )
            return

        self.options = {
            "chart_type": chart_type,
            "x_col": self.x_col_combo.currentData(),
            "y_col": self.y_col_combo.currentData(),
            "series_col": self.series_col_combo.currentData(),
            "title": self.title_edit.text().strip(),
            "x_label": self.x_label_edit.text().strip(),
            "y_label": self.y_label_edit.text().strip(),
            "palette": self.palette_combo.currentText() or "default",
            "group_by": self.group_by_combo.currentData(),
            "agg": self.agg_combo.currentText() or "mean",
        }
        self.accept()

    def get_options(self) -> dict[str, Any]:
        return self.options
