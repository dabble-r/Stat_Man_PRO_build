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
        
        This constructor sets up the dialog's UI structure based on the provided template.
        The template defines the dialog's appearance and behavior (inputs, selections, buttons),
        while the context provides runtime data needed by handlers (league, selected items, etc.).
        
        Args:
            template: Dictionary containing dialog configuration:
                - 'title': Window title string
                - 'size': Tuple of (width, height) for dialog size
                - 'layout': Layout type ('standard', 'vertical', 'custom')
                - 'inputs': Input field configuration(s)
                - 'selection': Radio button or checkbox configuration
                - 'buttons': Action button configuration(s)
                - 'custom_widgets': Custom widget configuration (date pickers, combo boxes, etc.)
                - 'custom_setup': Optional custom setup function
            context: Dictionary containing runtime context:
                - 'league': League instance
                - 'selected': Currently selected item(s)
                - 'leaderboard': Leaderboard instance
                - 'lv_teams': League view teams instance
                - 'stack': Undo/redo stack instance
                - 'undo': Undo manager instance
                - 'message': Message dialog instance
            parent: Parent widget for modal dialog behavior
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
        """
        Setup dialog UI based on template configuration.
        
        This method orchestrates the dialog setup process in the correct order:
        1. Sets window title and size
        2. Creates the layout structure
        3. Adds input fields (if configured)
        4. Adds selection widgets (radio buttons/checkboxes if configured)
        5. Adds action buttons (if configured)
        6. Adds custom inputs (e.g., custom order field for lineup)
        7. Adds custom widgets (date pickers, combo boxes, tree widgets)
        8. Applies any custom setup function if provided
        
        The order is important: custom inputs are added before custom_setup so that
        custom_setup functions can access and modify them.
        """
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
        """
        Setup main layout structure based on template layout type.
        
        Layout types:
        - 'standard': Two-column layout with inputs on left, selections on right, buttons at bottom
        - 'vertical': Single-column layout with all widgets stacked vertically
        - 'custom': Minimal layout setup; custom_setup function handles detailed layout
        
        Defaults to 'standard' layout if layout type is not specified or invalid.
        """
        layout_type = self.template.get('layout', 'standard')
        
        if layout_type == 'standard':
            self._setup_standard_layout()
        elif layout_type == 'vertical':
            self._setup_vertical_layout()
        elif layout_type == 'custom':
            # Custom layout will be handled by custom_setup function
            # This just creates a basic vertical layout container
            self.main_layout = QVBoxLayout()
            self.setLayout(self.main_layout)
        else:
            # Fallback to standard layout for unknown types
            self._setup_standard_layout()
    
    def _setup_standard_layout(self):
        """
        Setup standard two-column layout structure.
        
        Layout structure:
        - Main vertical layout with stretch at top and bottom
        - Horizontal content layout in the middle containing:
          * Form widget (left): Input fields with labels
          * Spacing (40px) between form and selection if both exist
          * Selection widget (right): Radio buttons or checkboxes
        - Button layout at bottom (horizontal or vertical based on template)
        
        This is the most common layout for stat update dialogs where users
        enter a value on the left and select an option on the right.
        """
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
        """
        Setup single-column vertical layout structure.
        
        All widgets are stacked vertically in order:
        1. Input fields (if configured)
        2. Selection widgets (if configured)
        3. Action buttons
        
        This layout is used for simpler dialogs like confirmation dialogs
        or dialogs that don't need the two-column structure.
        """
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
        """
        Setup input fields based on template configuration.
        
        Supports two input configurations:
        - Single input: Dictionary with input configuration
        - Multiple inputs: List of input configuration dictionaries
        
        Each input is created with a unique key ('input' for single, 'input_0', 'input_1', etc. for multiple)
        and stored in self.input_fields for later retrieval.
        """
        inputs = self.template['inputs']
        
        if isinstance(inputs, dict):
            # Single input field configuration
            self._create_input('input', inputs)
        elif isinstance(inputs, list):
            # Multiple input fields configuration
            for i, input_config in enumerate(inputs):
                self._create_input(f'input_{i}', input_config)
    
    def _create_input(self, key: str, config: Dict[str, Any]):
        """
        Create a single input field with label and validation.
        
        Args:
            key: Unique identifier for this input field (used to retrieve value later)
            config: Dictionary containing input configuration:
                - 'label': Label text displayed above input
                - 'type': Input type (currently only 'text' supported)
                - 'validator': Validation type ('integer', 'positive_integer') or QValidator instance
                - 'alignment': Text alignment (Qt.AlignCenter, Qt.AlignLeft, etc.)
                - 'default': Default value to pre-populate
                - 'visible': Whether input is initially visible (default: True)
        
        The input field is added to form_layout if it exists, and stored in
        self.input_fields dictionary for later access via get_input_value().
        """
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
        
        # Set validator to restrict input types
        # Supports string shortcuts, QValidator instances, or callable validators
        if validator:
            if isinstance(validator, str):
                # String shortcuts for common validators
                if validator == 'integer':
                    # Allows any integer (positive or negative)
                    input_field.setValidator(QIntValidator())
                elif validator == 'positive_integer':
                    # Only allows positive integers (1 to 999999)
                    input_field.setValidator(QIntValidator(1, 999999))
            elif isinstance(validator, QValidator):
                # Direct QValidator instance
                input_field.setValidator(validator)
            elif callable(validator):
                # Custom validator function that returns a QValidator
                input_field.setValidator(validator())
        
        # Store input
        self.input_fields[key] = input_field
        
        # Add to layout
        if hasattr(self, 'form_layout'):
            self.form_layout.addWidget(label)
            self.form_layout.addWidget(input_field)
    
    def _setup_selection(self):
        """
        Setup selection widgets (radio buttons or checkboxes) based on template.
        
        Selection type determines widget behavior:
        - 'radio': Single selection (mutually exclusive options)
        - 'checkbox': Multiple selection (can select multiple options)
        
        The selection configuration is passed to the appropriate setup method
        which creates the widgets and adds them to the selection layout.
        """
        selection = self.template['selection']
        selection_type = selection.get('type', 'radio')
        
        if selection_type == 'radio':
            # Single selection: only one option can be selected at a time
            self._setup_radio_buttons(selection)
        elif selection_type == 'checkbox':
            # Multiple selection: multiple options can be selected simultaneously
            self._setup_checkboxes(selection)
    
    def _setup_radio_buttons(self, config: Dict[str, Any]):
        """
        Setup radio button group with enablement logic and toggle handlers.
        
        Args:
            config: Dictionary containing radio button configuration:
                - 'group_key': Unique identifier for this button group (default: 'selection')
                - 'options': List of option strings to display
                - 'default': Default selected option (string or index)
                - 'enablement_logic': Function or boolean to control which options are enabled
                - 'toggle_handler': Function called when a radio button is toggled
        
        Enablement logic:
        - If callable: Called with (option, dialog) to determine if option should be enabled
        - If boolean: Applied to all options uniformly
        - If None: Only first option enabled by default (common for stat dialogs)
        
        Radio buttons are stored in self.radio_groups and self.radio_buttons dictionaries
        for later access via get_selected_option().
        """
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
            
            # Initial enablement: determines which options are available
            # This is commonly used to disable advanced stats until basic stats are entered
            if enablement_logic:
                if callable(enablement_logic):
                    # Dynamic enablement: function determines per-option enablement
                    # Called with (option_text, dialog_instance)
                    enabled = enablement_logic(option, self)
                    radio.setEnabled(enabled)
                else:
                    # Static enablement: boolean value applied to all options
                    radio.setEnabled(enablement_logic)
            else:
                # Default behavior: only first option enabled initially
                # This is typical for stat dialogs where 'hit' is always available
                # but other stats require at_bat > 0
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
        """
        Setup checkbox group for multiple selection scenarios.
        
        Args:
            config: Dictionary containing checkbox configuration:
                - 'group_key': Unique identifier for this checkbox group (default: 'selection')
                - 'options': List of option strings to display as checkboxes
                - 'change_handler': Optional function called when checkbox state changes
        
        Checkboxes allow multiple selections (unlike radio buttons which are exclusive).
        Used for scenarios like selecting multiple teams for a graph or multiple positions.
        
        Checkboxes are stored in self.checkbox_groups and self.checkboxes dictionaries
        for later access via get_selected_checkboxes().
        """
        group_key = config.get('group_key', 'selection')
        options = config.get('options', [])
        
        # Create button group (non-exclusive to allow multiple selections)
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
        """
        Setup action buttons based on template button configuration.
        
        Each button configuration can specify:
        - 'label': Button text
        - 'handler': Function called when button is clicked (receives dialog instance)
        - 'width': Fixed button width in pixels
        - 'visible': Whether button is initially visible (default: True)
        
        Buttons are added to button_layout (horizontal or vertical based on template)
        and stored in self.action_buttons dictionary for programmatic access.
        """
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
        """
        Get text value from an input field.
        
        Args:
            key: Input field key (default: 'input' for single input dialogs)
        
        Returns:
            Text content of the input field, or empty string if field doesn't exist
        
        Use this method in handlers to retrieve user-entered values from input fields.
        """
        if key in self.input_fields:
            return self.input_fields[key].text()
        return ''
    
    def get_selected_option(self, group_key: str = 'selection') -> Optional[str]:
        """
        Get the text of the currently selected radio button.
        
        Args:
            group_key: Radio button group identifier (default: 'selection')
        
        Returns:
            Text of the checked radio button, or None if no button is checked
        
        Use this method in handlers to determine which option the user selected
        from a radio button group.
        """
        if group_key in self.radio_groups:
            checked_button = self.radio_groups[group_key].checkedButton()
            if checked_button:
                return checked_button.text()
        return None
    
    def get_selected_checkboxes(self, group_key: str = 'selection') -> List[str]:
        """
        Get list of all checked checkbox option texts.
        
        Args:
            group_key: Checkbox group identifier (default: 'selection')
        
        Returns:
            List of text strings for all checked checkboxes (empty list if none checked)
        
        Use this method in handlers to retrieve all selected options from a checkbox group.
        """
        selected = []
        if group_key in self.checkboxes:
            for checkbox in self.checkboxes[group_key]:
                if checkbox.isChecked():
                    selected.append(checkbox.text())
        return selected
    
    def enable_selection_options(self, group_key: str = 'selection', enable: bool = True):
        """
        Enable or disable all options in a selection group.
        
        Args:
            group_key: Selection group identifier (default: 'selection')
            enable: True to enable all options, False to disable all
        
        This is useful for dynamically enabling/disabling selection options based on
        dialog state or user input. Works for both radio buttons and checkboxes.
        """
        if group_key in self.radio_buttons:
            for radio in self.radio_buttons[group_key]:
                radio.setEnabled(enable)
        elif group_key in self.checkboxes:
            for checkbox in self.checkboxes[group_key]:
                checkbox.setEnabled(enable)
    
    def show_validation_error(self, message: str):
        """
        Display a validation error message to the user.
        
        Args:
            message: Error message text to display
        
        Uses the message dialog instance from context to show a non-blocking
        error message (2 second timeout, no buttons). If no message instance
        is available, this method does nothing.
        """
        if self.message:
            self.message.show_message(message, btns_flag=False, timeout_ms=2000)
    
    def _setup_custom_input(self, config: Dict[str, Any]):
        """
        Setup a custom input field for special use cases.
        
        Custom inputs are additional input fields beyond the main input field.
        Common use case: custom batting order number input that appears when
        "custom" option is selected in lineup dialog.
        
        Args:
            config: Dictionary containing custom input configuration:
                - 'key': Unique identifier for this input (default: 'custom_input')
                - 'label': Optional label text
                - 'type': Input type (currently only 'text' supported)
                - 'width': Fixed width in pixels
                - 'visible': Initial visibility (default: False, shown when needed)
                - 'alignment': Text alignment ('center', 'left', 'right')
        
        The input is added to selection_layout if it exists, otherwise to form_layout.
        Stored in self.input_fields for access via get_custom_input_value().
        """
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
        """
        Get text value from a custom input field.
        
        Args:
            key: Custom input field key (e.g., 'custom_order' for lineup dialog)
        
        Returns:
            Text content of the custom input field, or empty string if not found
        
        Use this to retrieve values from custom inputs like the custom batting order number.
        """
        if key in self.input_fields:
            return self.input_fields[key].text()
        return ''
    
    def set_custom_input_visible(self, key: str, visible: bool):
        """
        Show or hide a custom input field dynamically.
        
        Args:
            key: Custom input field key
            visible: True to show, False to hide
        
        Useful for showing/hiding custom inputs based on user selection
        (e.g., show custom order input when "custom" option is selected).
        """
        if key in self.input_fields:
            self.input_fields[key].setVisible(visible)
    
    def _setup_custom_widgets(self):
        """
        Setup custom widgets beyond standard inputs and selections.
        
        Supported widget types:
        - 'date_edit': Date picker widget (QDateEdit) with calendar popup
        - 'combo_box': Dropdown selection widget (QComboBox)
        - 'tree_widget': Tree view widget (QTreeWidget) for displaying hierarchical data
        
        Each widget type has specific configuration options and can be placed
        in different layouts ('form', 'custom', or 'none' for manual placement).
        
        Custom widgets are stored in self.custom_widgets dictionary and can be
        accessed via get_custom_widget() and type-specific getter methods.
        """
        custom_widgets = self.template.get('custom_widgets', {})
        
        for widget_key, widget_config in custom_widgets.items():
            widget_type = widget_config.get('type')
            
            if widget_type == 'date_edit':
                # Date picker widget for selecting dates (e.g., season start/end dates)
                widget = QDateEdit(self)
                min_date = widget_config.get('min_date')  # Minimum selectable date
                max_date = widget_config.get('max_date')  # Maximum selectable date
                default_date = widget_config.get('default_date', QDate.currentDate())  # Initial date
                calendar_popup = widget_config.get('calendar_popup', True)  # Show calendar popup
                
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
                # Dropdown selection widget (e.g., "Select...", "Season Start", "Season End")
                widget = QComboBox(self)
                items = widget_config.get('items', [])  # List of option strings
                widget.addItems(items)
                enabled = widget_config.get('enabled', True)  # Initial enabled state
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
                # Tree view widget for displaying search results or hierarchical data
                widget = QTreeWidget(self)
                columns = widget_config.get('columns', 2)  # Number of columns
                headers = widget_config.get('headers', [])  # Column header labels
                visible = widget_config.get('visible', True)  # Initial visibility
                
                widget.setColumnCount(columns)
                if headers:
                    widget.setHeaderLabels(headers)
                widget.setVisible(visible)
                widget.setEditTriggers(widget.EditTrigger.NoEditTriggers)
                widget.setSelectionMode(widget.SelectionMode.SingleSelection)
                widget.setSelectionBehavior(widget.SelectionBehavior.SelectRows)  # Select entire row
                widget.header().setDefaultAlignment(Qt.AlignCenter)
                widget.header().setSectionResizeMode(widget.header().ResizeMode.Stretch)
                
                # Ensure items are selectable when added
                # This will be handled when items are added to the tree
                
                self.custom_widgets[widget_key] = widget
                
                # Add to main layout
                if hasattr(self, 'main_layout'):
                    self.main_layout.addWidget(widget)
    
    def get_custom_widget(self, key: str) -> Optional[QWidget]:
        """
        Get a custom widget instance by its key.
        
        Args:
            key: Widget key from custom_widgets configuration
        
        Returns:
            The widget instance (QDateEdit, QComboBox, QTreeWidget, etc.) or None if not found
        
        Use this to access custom widgets for direct manipulation or to pass to handlers.
        For type-specific access, use the dedicated getter methods (get_date_value, etc.).
        """
        return self.custom_widgets.get(key)
    
    def get_date_value(self, key: str) -> Optional[QDate]:
        """
        Get the selected date from a date edit widget.
        
        Args:
            key: Date edit widget key (e.g., 'date_edit')
        
        Returns:
            QDate object representing the selected date, or None if widget not found
        
        Use this to retrieve date values from date picker widgets in handlers.
        """
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QDateEdit):
            return widget.date()
        return None
    
    def get_combo_value(self, key: str) -> Optional[str]:
        """
        Get the currently selected text from a combo box widget.
        
        Args:
            key: Combo box widget key (e.g., 'date_combo')
        
        Returns:
            Text of the selected item, or None if widget not found
        
        Use this to retrieve the selected option text from combo boxes.
        """
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return None
    
    def get_combo_index(self, key: str) -> int:
        """
        Get the currently selected index from a combo box widget.
        
        Args:
            key: Combo box widget key
        
        Returns:
            Zero-based index of selected item, or -1 if widget not found or nothing selected
        
        Useful for checking if "Select..." (index 0) is selected vs. actual options.
        """
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            return widget.currentIndex()
        return -1
    
    def set_combo_enabled(self, key: str, enabled: bool):
        """
        Enable or disable a combo box widget.
        
        Args:
            key: Combo box widget key
            enabled: True to enable, False to disable
        
        Useful for dynamically enabling/disabling combo boxes based on user selection
        (e.g., enable date combo only when certain radio option is selected).
        """
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            widget.setEnabled(enabled)
    
    def set_combo_index(self, key: str, index: int):
        """
        Set the selected index of a combo box widget.
        
        Args:
            key: Combo box widget key
            index: Zero-based index to select
        
        Useful for resetting combo boxes to default state (e.g., index 0 for "Select...").
        """
        widget = self.custom_widgets.get(key)
        if isinstance(widget, QComboBox):
            widget.setCurrentIndex(index)
    
    def closeEvent(self, event: QCloseEvent):
        """
        Handle dialog close event (user clicking X or pressing Escape).
        
        Args:
            event: QCloseEvent containing close event information
        
        If a 'close_handler' is provided in the template, it is called with
        (event, dialog). The handler can call event.accept() to allow closing
        or event.ignore() to prevent closing (e.g., show confirmation dialog).
        
        If no handler is provided, the dialog closes normally (event.accept()).
        """
        close_handler = self.template.get('close_handler')
        if close_handler and callable(close_handler):
            # Custom close handler can show confirmation, save data, etc.
            close_handler(event, self)
        else:
            # Default: allow closing without confirmation
            event.accept()
    
    def validate(self) -> bool:
        """
        Validate dialog inputs before submission.
        
        Returns:
            True if validation passes, False if validation fails
        
        If a 'validation' function is provided in the template, it is called
        with the dialog instance. The function should return True if all inputs
        are valid, False otherwise. It can also call show_validation_error()
        to display error messages to the user.
        
        If no validation function is provided, returns True (no validation).
        
        This method can be called by button handlers before processing input.
        """
        validation = self.template.get('validation')
        if validation and callable(validation):
            # Custom validation function checks inputs and returns True/False
            return validation(self)
        # Default: no validation, assume inputs are valid
        return True

