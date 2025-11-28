# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause
from __future__ import annotations

"""PySide6 port of the line/bar example from Qt v5.x"""

import sys
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet,
    QBarCategoryAxis, QCategoryAxis, QValueAxis, QLineSeries
)
from decimal import Decimal, getcontext

class BarGraphWithDualAxes(QMainWindow):
    def __init__(self, data_bar=None, data_line=None):
        """Window rendering bar stats with a secondary AVG line on dual Y axes."""
        super().__init__()
        self.setWindowTitle("Team Stats with Batting Average")
        self.data_bar = data_bar 
        self.data_line = data_line 

        #Bar Series with 5 values per bar
        self._bar_series = QBarSeries()
        self.categories = ["Hits", "SO", "Runs", "ERA", "K"]
        
        # Line Series for Batting AVG (0–1.000 range)
        self._line_series = QLineSeries()
        self._line_series.setName("AVG")
        
        pen = QPen(QColor(Qt.black))
        pen.setWidth(3)  # Optional: make the line thicker
        self._line_series.setPen(pen)

        # Chart Setup
        self.chart = QChart()
        self.chart.setTitle("Team Performance")
        self.chart.addSeries(self._bar_series)
        self.chart.addSeries(self._line_series)

        # X Axis
        self._axis_x = QBarCategoryAxis()
        self._axis_x.append(self.categories)
        self.chart.addAxis(self._axis_x, Qt.AlignBottom)
        self._bar_series.attachAxis(self._axis_x)
        self._line_series.attachAxis(self._axis_x)

        # Left Y Axis (Bar values)
        self._axis_y1 = QValueAxis()
        self._axis_y1.setTitleText("Team Stats")
        self._axis_y1.setRange(0, 100)
        self.chart.addAxis(self._axis_y1, Qt.AlignLeft)
        self._bar_series.attachAxis(self._axis_y1)

        # 📐 Right Y Axis (Batting AVG)
        self._axis_y2 = QValueAxis()
        self._axis_y2.setTitleText("Batting AVG")
        self._axis_y2.setRange(0, 1.000)
        self.chart.addAxis(self._axis_y2, Qt.AlignRight)
        self._line_series.attachAxis(self._axis_y2)

        # Chart View
        self._chart_view = QChartView(self.chart)
        self._chart_view.setRenderHint(QPainter.Antialiasing)
        self.setCentralWidget(self._chart_view)

        # Legend
        self.chart.legend().setVisible(True)
        font = QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setBold(True)
        font.setItalic(False)
        self.chart.legend().setFont(font)
        self.chart.legend().setAlignment(Qt.AlignBottom)

    def set_y1_range(self):
        """Compute left-axis max from bar sets with a small headroom for readability."""
        lst = dir(self)
        max = 0
        for el in lst:
          if el == '_bar_series':
            ##print(el)
            temp = getattr(self, el) 
            for set in temp.barSets():
               for i in range(set.count()):
                  value = set.at(i)
                  if value > max:
                    max = value
                  ##print(f'value {value} at {i}')
        ret = round(max * 1.25)
        if len(str(ret)) >= 2:
          return round(ret, -1)
        return round(ret)
  
    def create_barset(self):
      """Build bar sets (and append AVG) from provided team data when one team selected."""
      # self._bar_series.append(team1)
      # list of tuples - team number and 
      bar_series = getattr(self, '_bar_series')
      if len(self.data_bar) == 1:
        self.categories.append('AVG')

        team_bar = self.data_bar[0]
        team_line = self.data_line[0]
        team, name, vals = team_bar
        team, name, avg = team_line

        #print('barset vals:', vals)
        vals.append(avg)
        #print('teating vals - avg', vals, avg)

        team = QBarSet(name)

        team.append(vals)
        bar_series.append(team)

      else:

        for team in self.data_bar:
          team, name, vals = team
          team = QBarSet(name)
          team.append(vals)
          bar_series.append(team)
    
    def create_line_series(self):
      # self._bar_series.append(team1)
      # list of tuples - team number and 
      line_series = getattr(self, '_line_series')
      for indx, team in enumerate(self.data_line):
        team, name, val = team
        val_float = float(val)
        temp = QPointF(indx, val_float)
        line_series.append(temp)


class BarGraph(QMainWindow):
  def __init__(self, team_names, data_points, stat_names):
      super().__init__()
      self.setWindowTitle("Team Stats Bar Graph")
      self.resize(1000, 600)

      assert len(team_names) <= 6
      assert all(len(stats) == 6 for stats in data_points)

      self.team_names = team_names
      self.data_points = data_points
      self.stat_names = stat_names
      self.colors = self._generate_colors()

      self.chart = QChart()
      self.series = QBarSeries()
      self.series.setBarWidth(0.9)  # tightly packed stats

      self._create_barsets()
      self._setup_axes()
      self._finalize_chart()

  def _generate_colors(self):
      return [
          QColor("#3498db"),  # hits
          QColor("#e74c3c"),  # so
          QColor("#2ecc71"),  # runs
          QColor("#9b59b6"),  # k
          QColor("#f1c40f"),  # era
          QColor("#000000")   # avg
      ]
  
  def set_context(self, val):
      c = getcontext().prec = val
      return c

  def isLen(self, x, y):
      return len(str(x)) > y

  def get_dec(self, x, val):
    c = self.set_context(val)
    dec = Decimal(x) / 1
    flag = self.isLen(dec, 4)
    if not flag:
        return dec 
    return round(dec, 3)

  def _create_barsets(self):
    self.series_list = []

    for stat_index, stat_name in enumerate(self.stat_names):
        series = QBarSeries()
        series.setLabelsVisible(True)
        series.setLabelsPosition(QBarSeries.LabelsPosition.LabelsCenter)
        
        #series.setLabelsFormat("@value ")
        series.setBarWidth(0.99)

        barset = QBarSet(stat_name)
        
        barset.setBrush(QBrush(self.colors[stat_index]))

        for team_stats in self.data_points:
            barset.append(team_stats[stat_index])

        series.append(barset)
        self.chart.addSeries(series)
        self.series_list.append(series)
  
  def get_max_range(self, val):
    if val % 4 == 0:
       return val + 4 
    else:
      while val % 4 != 0:
        val += 1
      return val

  def _setup_axes(self):
    # Create font for all text elements (12px)
    axis_font = QFont()
    axis_font.setPointSize(12)
    label_font = QFont()
    label_font.setPointSize(12)
    title_font = QFont()
    title_font.setPointSize(12)
    title_font.setBold(True)
    
    # X-axis with team names
    x_axis = QCategoryAxis()
    for i, team in enumerate(self.team_names):
        x_axis.append(team, i)
    x_axis.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
    x_axis.setTitleText("Teams")
    x_axis.setTitleFont(title_font)
    x_axis.setLabelsFont(label_font)
    self.chart.addAxis(x_axis, Qt.AlignBottom)
    for series in self.series_list:
        series.attachAxis(x_axis)

    # Left Y-axis for first 5 stats
    max_stat_value = max(value for team in self.data_points for value in team[:5])

    max_range = self.get_max_range(max_stat_value)
    y_axis_left = QValueAxis()
    y_axis_left.setRange(0, max_range)
    y_axis_left.setLabelFormat("%.0f")
    y_axis_left.setTitleText("Stat Values")
    y_axis_left.setTitleFont(title_font)
    y_axis_left.setLabelsFont(label_font)
    self.chart.addAxis(y_axis_left, Qt.AlignLeft)
    for series in self.series_list[:5]:
        series.attachAxis(y_axis_left)

    # Right Y-axis for avg
    self.y_axis_right = QValueAxis()
    self.y_axis_right.setRange(0, 1.0)
    self.y_axis_right.setTickInterval(0.100)
    self.y_axis_right.setTitleText("AVG")
    self.y_axis_right.setTitleFont(title_font)
    self.y_axis_right.setLabelsFont(label_font)
    self.y_axis_right.setLabelFormat("%.3f")
    self.chart.addAxis(self.y_axis_right, Qt.AlignRight)
    self.series_list[5].attachAxis(self.y_axis_right)

  def _finalize_chart(self):
      self.chart.addSeries(self.series)
      self.chart.setTitle("Team Performance Overview")
      
      # Set title font (12px, bold)
      title_font = QFont()
      title_font.setPointSize(12)
      title_font.setBold(True)
      self.chart.setTitleFont(title_font)
      
      # Set legend font (12px)
      legend_font = QFont()
      legend_font.setPointSize(12)
      self.chart.legend().setVisible(True)
      self.chart.legend().setFont(legend_font)
      self.chart.legend().setAlignment(Qt.AlignBottom)

      chart_view = QChartView(self.chart)
      #chart_view.setRenderHint(chart_view.RenderHint.Antialiasing)
      self.setCentralWidget(chart_view)

# Example usage
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    teams = ["Team A", "Team B", "Team C", "Team D", "Team E"]
    stats = ["hits", "so", "runs", "k", "era", "avg"]
    data = [
        [10, 5, 8, 7, 3, 0.5],
        [12, 6, 9, 5, 4, 0.50],
        [9, 4, 7, 6, 2, 0.50],
        [9, 4, 7, 6, 2, 0.50],
        [9, 4, 7, 6, 2, 0.50],
    ]

    window = BarGraph(teams, data, stats)
    window.show()
    sys.exit(app.exec())

    