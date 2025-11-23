"""
Base dialog class for modular dialog architecture.
Provides common functionality for all dialogs with template-based configuration.
"""
from typing import Dict, List, Optional, Callable, Any, Union
from PySide6.QtWidgets import (
    QDialog, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
    QHBoxLayout, QRadioButton, QButtonGroup, QCheckBox, QSizePolicy,
    QDateEdit, QComboBox, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtGui import QIntValidator, QValidator, QCloseEvent
from PySide6.QtCore import Qt, QDate


class BaseDialog(QDialog):
    """
    Base dialog class that provides common functionality for all dialogs.
    Configured via template system to handle different dialog types.
    """
    
    def __init__(self, template: Dict[str, Any], context: Dict[str, Any], parent: Optional[QWidget] = None):
        """
        Initialize base dialog with template configuration and context.
        
        Args:
            template: Dictionary containing dialog configuration (title, inputs, selections, buttons, etc.)
            context: Dictionary containing runtime context (league, selected, stack, undo, message, etc.)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.template = template
        self.context = context
        
        # Extract common context items
        self.league = context.get('league')
        self.selected = context.get('selected')
        self.leaderboard = context.get('leaderboard')
        self.lv_teams = context.get('lv_teams')
        self.stack = context.get('stack')
        self.undo = context.get('undo')
        self.message = context.get('message')
        
        # UI components
        self.input_fields: Dict[str, QLineEdit] = {}
        self.custom_widgets: Dict[str, QWidget] = {}  # For date pickers, combo boxes, tree widgets, etc.
        self.radio_groups: Dict[str, QButtonGroup] = {}
        self.radio_buttons: Dict[str, List[QRadioButton]] = {}
        self.checkbox_groups: Dict[str, QButtonGroup] = {}
        self.checkboxes: Dict[str, List[QCheckBox]] = {}
        self.action_buttons: Dict[str, QPushButton] = {}
        
        # Setup dialog
        self._setup_dialog()
    
    def _setup_dialog(self):
        """Setup dialog based on template configuration."""
        # Set window title
        title = self.template.get('title', 'Dialog')
        self.setWindowTitle(title)
        
        # Set size
        size = self.template.get('size', (400, 300))
        self.resize(size[0], size[1])
        
        # Setup layout
        self._setup_layout()
        
        # Setup input fields
        if 'inputs' in self.template:
            self._setup_inputs()
        
        # Setup selection widgets (radio buttons or checkboxes)
        if 'selection' in self.template:
            self._setup_selection()
        
        # Setup buttons
        if 'buttons' in self.template:
            self._setup_buttons()
        
        # Setup custom inputs if provided (before custom_setup so custom_setup can access them)
        if 'custom_input' in self.template:
            self._setup_custom_input(self.template['custom_input'])
        
        # Setup custom widgets if provided
        if 'custom_widgets' in self.template:
            self._setup_custom_widgets()
        
        # Apply custom setup if provided
        if 'custom_setup' in self.template:
            custom_setup = self.template['custom_setup']
            if callable(custom_setup):
                custom_setup(self)
    
    def _setup_layout(self):
        """Setup main layout structure."""
        layout_type = self.template.get('layout', 'standard')
        
        if layout_type == 'standard':
            self._setup_standard_layout()
        elif layout_type == 'vertical':
            self._setup_vertical_layout()
        elif layout_type == 'custom':
            # Custom layout will be handled by custom_setup
            self.main_layout = QVBoxLayout()
            self.setLayout(self.main_layout)
        else:
            self._setup_standard_layout()
    
    def _setup_standard_layout(self):
        """Setup standard layout: input on left, selection on right, buttons at bottom."""
        self.main_layout = QVBoxLayout()
        self.main_layout.addStretch()
        
        # Content layout (horizontal)
        self.content_layout = QHBoxLayout()
        self.content_layout.addStretch()
        
        # Form widget (left side)
        if 'inputs' in self.template:
            self.form_widget = QWidget()
            self.form_layout = QVBoxLayout()
            self.form_widget.setLayout(self.form_layout)
            self.form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.content_layout.addWidget(self.form_widget)
        
        # Spacing
        if 'inputs' in self.template and 'selection' in self.template:
            self.content_layout.addSpacing(40)
        
        # Selection widget (right side)
        if 'selection' in self.template:
            self.selection_widget = QWidget()
            self.selection_layout = QVBoxLayout()
            self.selection_layout.setAlignment(Qt.AlignTop)
            self.selection_widget.setLayout(self.selection_layout)
            self.content_layout.addWidget(self.selection_widget)
        
        self.content_layout.addStretch()
        
        # Add content to main layout
        self.main_layout.addLayout(self.content_layout)
        self.main_layout.addSpacing(20)
        
        # Button layout (can be horizontal or vertical based on template)
        button_layout_type = self.template.get('button_layout', 'horizontal')
        if button_layout_type == 'vertical':
            self.button_layout = QVBoxLayout()
        else:
            self.button_layout = QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)
        
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)
    
    def _setup_vertical_layout(self):
        """Setup vertical layout: all widgets stacked vertically."""
        self.main_layout = QVBoxLayout()
        self.main_layout.addStretch()
        
        # Form layout
        if 'inputs' in self.template:
            self.form_layout = QVBoxLayout()
            self.main_layout.addLayout(self.form_layout)
        
        # Selection layout
        if 'selection' in self.template:
            self.selection_layout = QVBoxLayout()
            self.selection_layout.setAlignment(Qt.AlignTop)
            self.main_layout.addLayout(self.selection_layout)
        
        # Button layout
        self.button_layout = QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)
        
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)
    
    def _setup_inputs(self):
        """Setup input fields based on template configuration."""
        inputs = self.template['inputs']
        
        if isinstance(inputs, dict):
            # Single input
            self._create_input('input', inputs)
        elif isinstance(inputs, list):
            # Multiple inputs
            for i, input_config in enumerate(inputs):
                self._create_input(f'input_{i}', input_config)
    
    def _create_input(self, key: str, config: Dict[str, Any]):
        """Create a single input field."""
        label_text = config.get('label', 'Enter value:')
        input_type = config.get('type', 'text')
        validator = config.get('validator')
        alignment = config.get('alignment', Qt.AlignCenter)
        default_value = config.get('default', '')
        visible = config.get('visible', True)
        
        # Create label
        label = QLabel(label_text)
        label.setAlignment(alignment)
        
        # Create input
        input_field = QLineEdit()
        input_field.setAlignment(alignment)
        input_field.setText(default_value)
        input_field.setVisible(visible)
        
        # Set validator
        if validator:
            if isinstance(validator, str):
                if validator == 'integer':
                    input_field.setValidator(QIntValidator())
                elif validator == 'positive_integer':
                    input_field.setValidator(QIntValidator(1, 999999))
            elif isinstance(validator, QValidator):
                input_field.setValidator(validator)
            elif callable(validator):
                # Custom validator function
                input_field.setValidator(validator())
        
        # Store input
        self.input_fields[key] = input_field
        
        # Add to layout
        if hasattr(self, 'form_layout'):
            self.form_layout.addWidget(label)
            self.form_layout.addWidget(input_field)
    
    def _setup_selection(self):
        """Setup selection widgets (radio buttons or checkboxes)."""
        selection = self.template['selection']
        selection_type = selection.get('type', 'radio')
        
        if selection_type == 'radio':
            self._setup_radio_buttons(selection)
        elif selection_type == 'checkbox':
            self._setup_checkboxes(selection)
    
    def _setup_radio_buttons(self, config: Dict[str, Any]):
        """Setup radio button group."""
        group_key = config.get('group_key', 'selection')
        options = config.get('options', [])
        default = config.get('default')
        enablement_logic = config.get('enablement_logic')
        
        # Create button group
        radio_group = QButtonGroup(self)
        radio_buttons = []
        
        # Create radio buttons
        for i, option in enumerate(options):
            radio = QRadioButton(str(option))
            
            # Set default
            if default is not None and (option == default or i == default):
                radio.setChecked(True)
            
            # Initial enablement
            if enablement_logic:
                if callable(enablement_logic):
                    # Check if this option should be enabled
                    enabled = enablement_logic(option, self)
                    radio.setEnabled(enabled)
                else:
                    # Simple enablement check
                    radio.setEnabled(enablement_logic)
            else:
                # Default: only first option enabled
                if i == 0:
                    radio.setEnabled(True)
                else:
                    radio.setEnabled(False)
            
            # Connect toggle handler if provided
            toggle_handler = config.get('toggle_handler')
            if toggle_handler and callable(toggle_handler):
                radio.toggled.connect(lambda checked, opt=option: toggle_handler(opt, checked, self))
            
            radio_group.addButton(radio, i)
            radio_buttons.append(radio)
            
            # Add to layout
            if hasattr(self, 'selection_layout'):
                self.selection_layout.addWidget(radio)
        
        # Store references
        self.radio_groups[group_key] = radio_group
        self.radio_buttons[group_key] = radio_buttons
    
    def _setup_checkboxes(self, config: Dict[str, Any]):
        """Setup checkbox group."""
        group_key = config.get('group_key', 'selection')
        options = config.get('options', [])
        
        # Create button group
        checkbox_group = QButtonGroup(self)
        checkbox_group.setExclusive(False)  # Allow multiple selections
        checkboxes = []
        
        # Create checkboxes
        for i, option in enumerate(options):
            checkbox = QCheckBox(str(option))
            
            # Connect change handler if provided
            change_handler = config.get('change_handler')
            if change_handler and callable(change_handler):
                checkbox.stateChanged.connect(lambda state, opt=option: change_handler(opt, state, self))
            
            checkbox_group.addButton(checkbox, i)
            checkboxes.append(checkbox)
            
            # Add to layout
            if hasattr(self, 'selection_layout'):
                self.selection_layout.addWidget(checkbox)
        
        # Store references
        self.checkbox_groups[group_key] = checkbox_group
        self.checkboxes[group_key] = checkboxes
    
    def _setup_buttons(self):
        """Setup action buttons."""
        buttons = self.template['buttons']
        
        for button_key, button_config in buttons.items():
            if isinstance(button_config, dict):
                label = button_config.get('label', button_key.title())
                handler = button_config.get('handler')
                width = button_config.get('width', 100)
                visible = button_config.get('visible', True)
                
                button = QPushButton(label)
                button.setFixedWidth(width)
                button.setVisible(visible)
                
                # Connect handler
                if handler and callable(handler):
                    button.clicked.connect(lambda checked=False, h=handler: h(self))
                
                self.action_buttons[button_key] = button
                
                # Add to layout
                if hasattr(self, 'button_layout'):
                    self.button_layout.addWidget(button, alignment=Qt.AlignCenter)
    
    def get_input_value(self, key: str = 'input') -> str:
        """Get value from input field."""
        if key in self.input_fields:
            return self.input_fields[key].text()
        return ''
    
    def get_selected_option(self, group_key: str = 'selection') -> Optional[str]:
        """Get selected radio button option."""
        if group_key in self.radio_groups:
            checked_button = self.radio_groups[group_key].checkedButton()
            if checked_button:
                return checked_button.text()
        return None
    
    def get_selected_checkboxes(self, group_key: str = 'selection') -> List[str]:
        """Get list of selected checkbox options."""
        selected = []
        if group_key in self.checkboxes:
            for checkbox in self.checkboxes[group_key]:
                if checkbox.isChecked():
                    selected.append(checkbox.text())
        return selected
    
    def enable_selection_options(self, group_key: str = 'selection', enable: bool = True):
        """Enable or disable all selection options."""
        if group_key in self.radio_buttons:
            for radio in self.radio_buttons[group_key]:
                radio.setEnabled(enable)
        elif group_key in self.checkboxes:
            for checkbox in self.checkboxes[group_key]:
                checkbox.setEnabled(enable)
    
    def show_validation_error(self, message: str):
        """Show validation error message."""
        if self.message:
            self.message.show_message(message, btns_flag=False, timeout_ms=2000)
    
    def _setup_custom_input(self, config: Dict[str, Any]):
        """Setup custom input field (e.g., custom order input for lineup)."""
        key = config.get('key', 'custom_input')
        label_text = config.get('label', '')
        input_type = config.get('type', 'text')
        width = config.get('width', 100)
        visible = config.get('visible', False)
        alignment = config.get('alignment', 'center')
        
        # Create input
        input_field = QLineEdit()
        input_field.setFixedWidth(width)
        input_field.setVisible(visible)
        
        if alignment == 'center':
            input_field.setAlignment(Qt.AlignCenter)
        
        # Store input
        self.input_fields[key] = input_field
        
        # Add to selection layout if it exists
        if hasattr(self, 'selection_layout'):
            if label_text:
                label = QLabel(label_text)
                self.selection_layout.addWidget(label)
            self.selection_layout.addWidget(input_field)
        elif hasattr(self, 'form_layout'):
            # Fallback to form layout if selection layout doesn't exist
            if label_text:
                label = QLabel(label_text)
                self.form_layout.addWidget(label)
            self.form_layout.addWidget(input_field)
    
    def get_custom_input_value(self, key: str) -> str:
        """Get value from custom input field."""
        if key in self.input_fields:
            return self.input_fields[key].text()
        return ''
    
    def set_custom_input_visible(self, key: str, visible: bool):
        """Show or hide custom input field."""
        if key in self.input_fields:
            self.input_fields[key].setVisible(visible)
    
    def _setup_custom_widgets(self):
        """Setup custom widgets like date pickers, combo boxes, tree widgets."""
        custom_widgets = self.template.get('custom_widgets', {})
        
        for widget_key, widget_config in custom_widgets.items():
            widget_type = widget_config.get('type')
            
            if widget_type == 'date_edit':
                widget = QDateEdit(self)
                min_date = widget_config.get('min_date')
                max_date = widget_config.get('max_date')
                default_date = widget_config.get('default_date', QDate.currentDate())
                calendar_popup = widget_config.get('calendar_popup', True)
                
                if min_date:
                    widget.setMinimumDate(min_date)
                if max_date:
                    widget.setMaximumDate(max_date)
                widget.setDate(default_date)
                widget.setCalendarPopup(calendar_popup)
                
                # Connect date changed handler if provided
                date_handler = widget_config.get('date_changed_handler')
                if date_handler and callable(date_handler):
                    widget.dateChanged.connect(lambda date: date_handler(date, self))
                
                self.custom_widgets[widget_key] = widget
                
                # Add to layout if specified
                layout_key = widget_config.get('layout', 'form')
                if layout_key == 'none':
                    # Widget will be manually added to layout
                    pass
                elif layout_key == 'form' and hasattr(self, 'form_layout'):
                    label_text = widget_config.get('label', '')
                    if label_text:
                        label = QLabel(label_text)
                        self.form_layout.addWidget(label)
                    self.form_layout.addWidget(widget)
                elif layout_key == 'custom' and hasattr(self, 'content_layout'):
                    self.content_layout.addWidget(widget)
            
            elif widget_type == 'combo_box':
                widget = QComboBox(self)
                items = widget_config.get('items', [])
                widget.addItems(items)
                enabled = widget_config.get('enabled', True)
                widget.setEnabled(enabled)
                
                # Connect handlers
                activated_handler = widget_config.get('activated_handler')
                if activated_handler and callable(activated_handler):
                    widget.activated.connect(lambda index: activated_handler(index, self))
                
                text_changed_handler = widget_config.get('text_changed_handler')
                if text_changed_handler and callable(text_changed_handler):
                    widget.currentTextChanged.connect(lambda text: text_changed_handler(text, self))
                
                self.custom_widgets[widget_key] = widget
                
                # Add to layout
                layout_key = widget_config.get('layout', 'form')
                if layout_key == 'none':
                    # Widget will be manually added to layout
                    pass
                elif layout_key == 'form' and hasattr(self, 'form_layout'):
                    self.form_layout.addWidget(widget)
                elif layout_key == 'custom' and hasattr(self, 'content_layout'):
                    self.content_layout.addWidget(widget)
            
            elif widget_type == 'tree_widget':
                widget = QTreeWidget(self)
                columns = widget_config.get('columns', 2)
                headers = widget_config.get('headers', [])
                visible = widget_config.get('visible', True)
                
                widget.setColumnCount(columns)
                if headers:
                    widget.setHeaderLabels(headers)
                widget.setVisible(visible)
                widget.setEditTriggers(widget.EditTrigger.NoEditTriggers)
                widget.setSelectionMode(widget.SelectionMode.SingleSelection)
                widget.header().setDefaultAlignment(Qt.AlignCenter)
                widget.header().setSectionResizeMode(widget.header().ResizeMode.Stretch)
                
                self.custom_widgets[widget_key] = widget
                
                # Add to main layout
                if hasattr(self, 'main_layout'):
                    self.main_layout.addWidget(widget)
    
    def get_custom_widget(self, key: str) -> Optional[QWidget]:
        """Get custom widget by key."""
        return self.custom_widgets.get(key)
    
    def get_date_value(self, key: str) -> Optional[QDate]:
        """Get date value from date edit widget."""
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QDateEdit):
            return widget.date()
        return None
    
    def get_combo_value(self, key: str) -> Optional[str]:
        """Get selected value from combo box."""
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return None
    
    def get_combo_index(self, key: str) -> int:
        """Get selected index from combo box."""
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            return widget.currentIndex()
        return -1
    
    def set_combo_enabled(self, key: str, enabled: bool):
        """Enable or disable combo box."""
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            widget.setEnabled(enabled)
    
    def set_combo_index(self, key: str, index: int):
        """Set combo box current index."""
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            widget.setCurrentIndex(index)
    
    def closeEvent(self, event: QCloseEvent):
        """Handle close event. Can be overridden by template."""
        close_handler = self.template.get('close_handler')
        if close_handler and callable(close_handler):
            close_handler(event, self)
        else:
            event.accept()
    
    def validate(self) -> bool:
        """Validate dialog inputs. Override in templates if needed."""
        validation = self.template.get('validation')
        if validation and callable(validation):
            return validation(self)
        return True

