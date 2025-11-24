"""
Template configurations for different dialog types.
Each template defines the structure and behavior of a specific dialog.
"""
from typing import Dict, Any, Callable, Optional, List, Tuple
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt


class DialogTemplate:
    """Base class for dialog templates."""
    
    @staticmethod
    def create_template() -> Dict[str, Any]:
        """Create and return template configuration dictionary."""
        raise NotImplementedError("Subclasses must implement create_template")


class StatUpdateTemplate(DialogTemplate):
    """Template for stat update dialogs (offense, pitching, team stats)."""
    
    @staticmethod
    def create_template(
        title: str,
        stat_options: List[str],
        default_stat: Optional[str] = None,
        update_handler: Optional[Callable] = None,
        undo_handler: Optional[Callable] = None,
        view_handler: Optional[Callable] = None,
        enablement_check: Optional[Callable] = None,
        validation: Optional[Callable] = None,
        input_label: str = "Enter value:",
        input_validator: str = "positive_integer"
    ) -> Dict[str, Any]:
        """
        Create template for stat update dialog.
        
        Args:
            title: Dialog window title
            stat_options: List of stat option labels
            default_stat: Default selected stat (or first option if None)
            update_handler: Function to handle stat update
            undo_handler: Function to handle undo
            view_handler: Function to handle view stats
            enablement_check: Function to check if options should be enabled
            validation: Custom validation function
            input_label: Label for input field
            input_validator: Validator type ('integer', 'positive_integer', or QValidator instance)
        """
        template = {
            'title': title,
            'size': (400, 300),
            'layout': 'standard',
            'inputs': {
                'label': input_label,
                'type': 'integer',
                'validator': input_validator,
                'alignment': Qt.AlignCenter
            },
            'selection': {
                'type': 'radio',
                'group_key': 'stats',
                'options': stat_options,
                'default': default_stat if default_stat else stat_options[0] if stat_options else None,
                'enablement_logic': enablement_check
            },
            'buttons': {}
        }
        
        # Set button layout to vertical for stat update dialogs
        template['button_layout'] = 'vertical'
        
        # Add submit button
        if update_handler:
            template['buttons']['submit'] = {
                'label': 'Submit',
                'width': 125,
                'handler': update_handler
            }
        
        # Add undo button
        if undo_handler:
            template['buttons']['undo'] = {
                'label': 'Undo',
                'width': 100,
                'handler': undo_handler
            }
        
        # Add view button
        if view_handler:
            template['buttons']['view'] = {
                'label': 'Current\nView',
                'width': 150,
                'handler': view_handler
            }
        
        # Add validation
        if validation:
            template['validation'] = validation
        
        return template


class AdminUpdateTemplate(DialogTemplate):
    """Template for admin/management update dialogs."""
    
    @staticmethod
    def create_template(
        title: str,
        options: List[str],
        default_option: Optional[str] = None,
        update_handler: Optional[Callable] = None,
        undo_handler: Optional[Callable] = None,
        toggle_handler: Optional[Callable] = None,
        input_label: str = "Enter value:",
        input_validator: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create template for admin update dialog.
        
        Args:
            title: Dialog window title
            options: List of admin option labels
            default_option: Default selected option
            update_handler: Function to handle update
            undo_handler: Function to handle undo
            toggle_handler: Function called when option is toggled (for conditional input visibility)
            input_label: Label for input field
            input_validator: Validator type or None for text input
        """
        template = {
            'title': title,
            'size': (400, 300),
            'layout': 'standard',
            'inputs': {
                'label': input_label,
                'type': 'text' if input_validator is None else 'integer',
                'validator': input_validator,
                'alignment': Qt.AlignCenter,
                'visible': True
            },
            'selection': {
                'type': 'radio',
                'group_key': 'admin',
                'options': options,
                'default': default_option if default_option else options[0] if options else None,
                'toggle_handler': toggle_handler
            },
            'buttons': {}
        }
        
        if update_handler:
            template['buttons']['submit'] = {
                'label': 'Submit',
                'width': 100,
                'handler': update_handler
            }
        
        if undo_handler:
            template['buttons']['undo'] = {
                'label': 'Undo',
                'width': 100,
                'handler': undo_handler
            }
        
        return template


class SelectionTemplate(DialogTemplate):
    """Template for selection dialogs (lineup, positions)."""
    
    @staticmethod
    def create_template(
        title: str,
        selection_options: List[str],
        input_label: str = "Enter Player:",
        default_option: Optional[str] = None,
        update_handler: Optional[Callable] = None,
        undo_handler: Optional[Callable] = None,
        toggle_handler: Optional[Callable] = None,
        custom_input_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create template for selection dialog.
        
        Args:
            title: Dialog window title
            selection_options: List of selection option labels
            input_label: Label for text input field
            default_option: Default selected option
            update_handler: Function to handle update
            undo_handler: Function to handle undo
            toggle_handler: Function called when option is toggled
            custom_input_config: Optional config for custom input field (e.g., custom order input)
        """
        template = {
            'title': title,
            'size': (400, 300),
            'layout': 'standard',
            'inputs': {
                'label': input_label,
                'type': 'text',
                'alignment': Qt.AlignCenter
            },
            'selection': {
                'type': 'radio',
                'group_key': 'selection',
                'options': selection_options,
                'default': default_option if default_option else selection_options[0] if selection_options else None,
                'toggle_handler': toggle_handler
            },
            'buttons': {}
        }
        
        if update_handler:
            template['buttons']['submit'] = {
                'label': 'Submit',
                'width': 100,
                'handler': update_handler
            }
        
        if undo_handler:
            template['buttons']['undo'] = {
                'label': 'Undo',
                'width': 100,
                'handler': undo_handler
            }
        
        # Add custom input if provided
        if custom_input_config:
            template['custom_input'] = custom_input_config
        
        return template


class ConfirmationTemplate(DialogTemplate):
    """Template for confirmation/removal dialogs."""
    
    @staticmethod
    def create_template(
        title: str,
        options: List[str],
        default_option: Optional[str] = None,
        submit_handler: Optional[Callable] = None,
        submit_label: str = "Submit"
    ) -> Dict[str, Any]:
        """
        Create template for confirmation dialog.
        
        Args:
            title: Dialog window title
            options: List of confirmation option labels
            default_option: Default selected option
            submit_handler: Function to handle submission
            submit_label: Label for submit button
        """
        template = {
            'title': title,
            'size': (400, 300),
            'layout': 'vertical',
            'selection': {
                'type': 'radio',
                'group_key': 'confirmation',
                'options': options,
                'default': default_option if default_option else options[0] if options else None
            },
            'buttons': {}
        }
        
        if submit_handler:
            template['buttons']['submit'] = {
                'label': submit_label,
                'width': 100,
                'handler': submit_handler
            }
        
        return template


class CreateEntityTemplate(DialogTemplate):
    """Template for creating new entities (player, team)."""
    
    @staticmethod
    def create_template(
        title: str,
        input_fields: List[Dict[str, Any]],
        checkbox_groups: Optional[List[Dict[str, Any]]] = None,
        submit_handler: Optional[Callable] = None,
        upload_handler: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Create template for entity creation dialog.
        
        Args:
            title: Dialog window title
            input_fields: List of input field configurations
            checkbox_groups: Optional list of checkbox group configurations
            submit_handler: Function to handle submission
            upload_handler: Function to handle file upload
        """
        template = {
            'title': title,
            'size': (650, 450),
            'layout': 'custom',
            'inputs': input_fields,
            'buttons': {}
        }
        
        if checkbox_groups:
            template['checkbox_groups'] = checkbox_groups
        
        if submit_handler:
            template['buttons']['submit'] = {
                'label': 'Submit',
                'width': 120,
                'handler': submit_handler
            }
        
        if upload_handler:
            template['buttons']['upload'] = {
                'label': 'Upload',
                'width': 100,
                'handler': upload_handler
            }
        
        return template


class CustomTemplate(DialogTemplate):
    """Template for custom/special dialogs."""
    
    @staticmethod
    def create_template(
        title: str,
        size: Tuple[int, int] = (400, 300),
        layout: str = 'standard',
        custom_setup: Optional[Callable] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create custom template with full control.
        
        Args:
            title: Dialog window title
            size: Dialog size (width, height)
            layout: Layout type ('standard', 'vertical', 'custom')
            custom_setup: Custom setup function
            **kwargs: Additional template configuration
        """
        template = {
            'title': title,
            'size': size,
            'layout': layout,
            **kwargs
        }
        
        if custom_setup:
            template['custom_setup'] = custom_setup
        
        return template


class ButtonMenuTemplate(DialogTemplate):
    """Template for hub/menu dialogs with multiple action buttons."""
    
    @staticmethod
    def create_template(
        title: str,
        buttons: List[Dict[str, Any]],
        size: Tuple[int, int] = (400, 300)
    ) -> Dict[str, Any]:
        """
        Create template for button menu dialog.
        
        Args:
            title: Dialog window title
            buttons: List of button configurations, each with 'label', 'width', 'handler'
            size: Dialog size
        """
        template = {
            'title': title,
            'size': size,
            'layout': 'vertical',
            'buttons': {}
        }
        
        for i, button_config in enumerate(buttons):
            key = button_config.get('key', f'button_{i}')
            template['buttons'][key] = button_config
        
        return template


class SearchTemplate(DialogTemplate):
    """Template for search dialogs with tree widget results."""
    
    @staticmethod
    def create_template(
        title: str,
        search_options: List[str],
        search_handler: Optional[Callable] = None,
        view_handler: Optional[Callable] = None,
        clear_handler: Optional[Callable] = None,
        input_label: str = "Enter value:"
    ) -> Dict[str, Any]:
        """
        Create template for search dialog.
        
        Args:
            title: Dialog window title
            search_options: List of search type options
            search_handler: Function to handle search
            view_handler: Function to handle view selected item
            clear_handler: Function to handle clear results
            input_label: Label for search input
        """
        template = {
            'title': title,
            'size': (500, 350),
            'layout': 'standard',
            'inputs': {
                'label': input_label,
                'type': 'text',
                'alignment': Qt.AlignCenter
            },
            'selection': {
                'type': 'radio',
                'group_key': 'search_type',
                'options': search_options,
                'default': search_options[0] if search_options else None,
                'enablement_logic': True  # All search options should be enabled from the start
            },
            'custom_widgets': {
                'search_tree': {
                    'type': 'tree_widget',
                    'columns': 2,
                    'headers': [],
                    'visible': False
                }
            },
            'buttons': {}
        }
        
        if search_handler:
            template['buttons']['submit'] = {
                'label': 'Submit',
                'width': 125,
                'handler': search_handler
            }
        
        if view_handler:
            template['buttons']['view'] = {
                'label': 'Current View',
                'width': 175,
                'handler': view_handler
            }
        
        if clear_handler:
            template['buttons']['clear'] = {
                'label': 'Clear',
                'width': 125,
                'handler': clear_handler
            }
        
        return template


class CheckboxSelectionTemplate(DialogTemplate):
    """Template for dialogs with checkbox selection."""
    
    @staticmethod
    def create_template(
        title: str,
        checkbox_options: List[str],
        submit_handler: Optional[Callable] = None,
        max_selections: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create template for checkbox selection dialog.
        
        Args:
            title: Dialog window title
            checkbox_options: List of checkbox option labels
            submit_handler: Function to handle submission
            max_selections: Maximum number of selections allowed
        """
        template = {
            'title': title,
            'size': (400, 300),
            'layout': 'vertical',
            'selection': {
                'type': 'checkbox',
                'group_key': 'selection',
                'options': checkbox_options,
                'max_selections': max_selections
            },
            'buttons': {}
        }
        
        if submit_handler:
            template['buttons']['submit'] = {
                'label': 'Submit',
                'width': 100,
                'handler': submit_handler
            }
        
        return template

