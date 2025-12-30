class StyleSheets():
    def __init__(self):
        #self.main_styles = self.get_monochrome_style()
        self.light_styles = self.get_monochrome_1_style()
        self.dark_styles = self.get_monochrome_2_style()
        

    
    def get_monochrome_1_style(self):
        return''' 
        * {
            font-family: "Segoe UI", sans-serif;
            font-size: 20px;
            color: #1a1a1a;
            background-color: #eeeeee;
        }

        QDialog {
            border: 2px solid #444444;
        }

        QGroupBox {
            border: 2px solid #444444;
            border-radius: 10px;
            margin-top: 10px;
            padding: 10px;
            background-color: #f0f0f0;
        }

        QLabel {
            font-size: 20px;
            font-weight: bold;
            color: #000000;
        }

        
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #666666;
            border-radius: 4px;
            padding: 6px;
            color: #1a1a1a;
            font-size: 16px;
        }

        QTreeWidget {
            font-size: 20px;
        }

        QTreeWidget::item:selected {
            background-color: #b7b7b7;   /* Highlight color */
            color: black;                /* Text color */
        }

        QTreeWidget::item:hover {
            background-color: #434343;   /* Optional hover effect */
            color: #f3f3f3;
        }

        QCheckBox {
            font-size: 18px;
        }

        QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 2px solid white;
        border-radius: 4px;
        background-color: black;
        }

        QCheckBox::indicator:checked {
            background-color: white;
            border: 2px solid black;
        }

        QCheckBox::indicator:unchecked {
            background-color: darkgray;
            border: 2px solid white;
        }

        QRadioButton {
            font-size: 18px;
        }

        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid white;
            border-radius: 8px;
            background-color: black;
        }

        QRadioButton::indicator:checked {
            background-color: white;
            border: 2px solid black;
        }

        QRadioButton::indicator:unchecked {
            background-color: darkgray;
            border: 2px solid white;
        }

        QPushButton {
            background-color: rgba(50, 50, 50, 0.9);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
        }

        
        QPushButton:hover {
            background-color: rgba(30, 30, 30, 0.5);
        }

        
        QPushButton:pressed {
            background-color: rgba(90, 90, 90, 1.0);
        }'''
 
    def get_monochrome_2_style(self):
        return'''
        * {
            font-family: "Segoe UI", sans-serif;
            font-size: 20px;
            color: #eeeeee;
            background-color: #1a1a1a;
        }

        QDialog {
            border: 2px solid #bbbbbb;
        }

        QGroupBox {
            border: 2px solid #bbbbbb;
            border-radius: 10px;
            margin-top: 10px;
            padding: 10px;
            background-color: #0f0f0f;
        }

        QLabel {
            font-size: 20px;
            font-weight: bold;
            color: #ffffff;
        }

        QLineEdit {
            background-color: #000000;
            border: 1px solid #999999;
            border-radius: 4px;
            padding: 6px;
            color: #eeeeee;
            font-size: 16px;
        }

        QTreeWidget {
            font-size: 20px;
        }

        QTreeWidget::item:selected {
            background-color: #484848;   /* Highlight color */
            color: white;                /* Text color */
        }

        QTreeWidget::item:hover {
            background-color: #cccccc;   /* Optional hover effect */
            color: #1a1a1a;
        }

        QCheckBox {
            font-size: 18px;
        }

        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid black;
            border-radius: 4px;
            background-color: white;
        }

        QCheckBox::indicator:checked {
            background-color: black;
            border: 2px solid white;
        }

        QCheckBox::indicator:unchecked {
            background-color: darkgray;
            border: 2px solid black;
        }

        QRadioButton {
            font-size: 18px;
        }

        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid black;
            border-radius: 8px;
            background-color: white;
        }

        QRadioButton::indicator:checked {
            background-color: black;
            border: 2px solid white;
        }

        QRadioButton::indicator:unchecked {
            background-color: darkgray;
            border: 2px solid black;
        }

        QPushButton {
            background-color: rgba(230, 230, 230, 0.9);
            color: black;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
        }

        QPushButton:hover {
            background-color: rgba(200, 200, 200, 0.5);
        }

        QPushButton:pressed {
            background-color: rgba(160, 160, 160, 1.0);
        }
    '''
   
    
    
   