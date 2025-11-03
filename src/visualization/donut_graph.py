# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause
from __future__ import annotations
import random

"""PySide6 port of the Donut Chart Breakdown example from Qt v5.x"""

import sys
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice

class MainSlice(QPieSlice):
    def __init__(self, breakdown_series, parent=None):
        """A central pie slice that mirrors the sum of its breakdown series."""
        super().__init__(parent)

        self.breakdown_series = breakdown_series
        self.name = None

        self.percentageChanged.connect(self.update_label)

    def get_breakdown_series(self):
        """Return the QPieSeries providing sub-slices for this main slice."""
        return self.breakdown_series

    def set_name(self, name):
        """Set display name for this main slice (used in labels)."""
        self.name = name

    def name(self):
        return self.name

    @Slot()
    def update_label(self):
        """Update centered label to show name and current percentage."""
        p = self.percentage() * 100
        self.setLabel(f"{self.name} {p:.2f}%")

class DonutBreakdownChart(QChart):
    def __init__(self, data, colors=[], parent=None):
        """Donut chart with outer breakdown rings built from input data series."""
        super().__init__(QChart.ChartTypeCartesian,
                         parent, Qt.WindowFlags())
        self.main_series = QPieSeries()
        self.main_series.setPieSize(0.7)
        self.addSeries(self.main_series)
        self.raw_data = data
        self.colors = colors
        self.color = Qt.red
        self.series_dict = {}

    def add_breakdown_series(self, breakdown_series, color):
        """Add a breakdown series as outer ring and a matching main slice segment."""
        font = QFont("Arial", 14)

        # add breakdown series as a slice to center pie
        main_slice = MainSlice(breakdown_series)
        main_slice.set_name(breakdown_series.name())
        main_slice.setValue(breakdown_series.sum())
        self.main_series.append(main_slice)

        # customize the slice
        main_slice.setBrush(color)
        main_slice.setLabelVisible()
        main_slice.setLabelColor(Qt.white)
        main_slice.setLabelPosition(QPieSlice.LabelInsideHorizontal)
        main_slice.setLabelFont(font)

        # position and customize the breakdown series
        breakdown_series.setPieSize(0.8)
        breakdown_series.setHoleSize(0.7)
        breakdown_series.setLabelsVisible()

        for pie_slice in breakdown_series.slices():
            #print("pie slice:", pie_slice, dir(pie_slice), pie_slice.value())
            slice_val = pie_slice.value()
            if slice_val == 0.0:
               pie_slice.setLabelVisible(False)
            color = QColor(color).lighter(115)
            pie_slice.setBrush(color)
            pie_slice.setLabelFont(font)

        # add the series to the chart
        self.addSeries(breakdown_series)

        # recalculate breakdown donut segments
        self.recalculate_angles()

        # update customize legend markers
        self.update_legend_markers()

    def recalculate_angles(self):
        """Recompute start/end angles for each breakdown ring from main slice percents."""
        angle = 0
        slices = self.main_series.slices()
        for pie_slice in slices:
            #print("pie slice:", pie_slice)
            breakdown_series = pie_slice.get_breakdown_series()
            breakdown_series.setPieStartAngle(angle)
            angle += pie_slice.percentage() * 360.0  # full pie is 360.0
            breakdown_series.setPieEndAngle(angle)

    def update_legend_markers(self):
        """Hide main-series legend markers; annotate breakdown markers with percentages."""
        # go through all markers
        for series in self.series():
            markers = self.legend().markers(series)
            for marker in markers:
                if series == self.main_series:
                    # hide markers from main series
                    marker.setVisible(False)
                else:
                    # modify markers from breakdown series
                    label = marker.slice().label()
                    p = marker.slice().percentage() * 100
                    marker.setLabel(f"{label} {p:.2f}%")
                    marker.setFont(QFont("Arial", 14))
    
    def pop_dict(self):
      for indx, el in enumerate(self.raw_data):
        ##print(indx, el)
        series = QPieSeries()
        ##print(el)

        resource = el['Resource']
        series.setName(resource)

        self.series_dict[resource] = []

        amount = el['Amount']

        for el in amount:
            ##print(el)
            type, num = list(el.keys()) + list(el.values()) 
            ##print(type, num)
            series.append(type, num)
        self.series_dict[resource].append(series)
            ##print(series_dic)
    
    # experimental - graph view 
    def pop_dict_exp(self, r_key, a_key):
      reset_r = r_key 
      reset_a = a_key

      for indx, el in enumerate(self.raw_data):
        ##print(indx, el)
        series = QPieSeries()

        r_key = reset_r
        a_key = reset_a

        r_key = r_key + f'_{str(indx+1)}'
        stat = el[r_key]
        
        series.setName(stat)

        self.series_dict[stat] = []

        a_key = a_key + f'_{str(indx+1)}'
        amount = el[a_key]

        for el in amount:
            #print(el)
            type, num = list(el.keys()) + list(el.values()) 
            #print("donut graph:", type, num)
            series.append(type, num)

        self.series_dict[stat].append(series)
        #print(series_dic)
    
    def add_breakdowns(self):
      #print("add breakdown:", self.series_dict)
      for el in self.series_dict:
        series_lst = self.series_dict[el]
        #print("series el:", self.series_dict[el][0], dir(self.series_dict[el][0]))
        for series in series_lst:
          #print("series:", series)
          color = self.get_rand_color(self.colors, self.series_dict)
          self.add_breakdown_series(series, color)
    
    def get_rand_color(self, colors, dict):
      if len(colors) == 0:
        return self.color 
      
      for el in dict:
        ##print(el)
        rand = random.randint(0, len(colors)-1)

        check = colors[rand]

        if check in colors:
          indx = colors.index(check)
          colors.pop(indx)
          return check
        
        rand = random.randint(0, len(colors)-1)
    
    
        
          
        
        
        


'''if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Graph is based on data of:
    #    'Total consumption of energy increased by 10 per cent in 2010'
    # Statistics Finland, 13 December 2011
    # http://www.stat.fi/til/ekul/2010/ekul_2010_2011-12-13_tie_001_en.html
    
    colors = [Qt.red, Qt.darkRed, Qt.green, Qt.darkGreen, Qt.blue, Qt.darkBlue, Qt.magenta, Qt.darkMagenta, Qt.cyan, Qt.darkCyan, Qt.yellow, Qt.darkYellow, Qt.gray, Qt.darkGray, Qt.lightGray, Qt.transparent]

    player = Player('Nick Broussard', 18, 'Beef Sliders', 'hello', ['second base', 'pitcher', 'left field'])
    player.at_bat = 40
    player.so = 5
    player.bb = 5 
    player.hit = 5 
    player.sac_fly = 5 
    player.hr = 5 
    player.rbi = 5 
    player.singles = 5 
    player.doubles = 5 
    player.triples = 5
    
    data_test_player_exp = player.graph_view_format_player()

    donut_breakdown = DonutBreakdownChart(data_test_player_exp, colors)
    donut_breakdown.setAnimationOptions(QChart.AllAnimations)
    donut_breakdown.setTitle("Total consumption of energy in Finland 2010")
    donut_breakdown.legend().setAlignment(Qt.AlignRight)

    donut_breakdown.pop_dict_exp('Stat', 'Amount')

    #series_dict = donut_breakdown.series_dict

    donut_breakdown.add_breakdowns()

    window = QMainWindow()
    chart_view = QChartView(donut_breakdown)
    chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
    window.setCentralWidget(chart_view)
    available_geometry = window.screen().availableGeometry()
    size = available_geometry.height() * 0.75
    window.resize(size, size * 0.8)
    window.show()

    sys.exit(app.exec())
'''