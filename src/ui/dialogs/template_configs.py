"""
Pre-configured template factories for common dialog types.
These functions create ready-to-use templates for specific dialog use cases.
"""
from typing import Dict, Any, Callable, Optional, List
from src.ui.dialogs.dialog_templates import (
    StatUpdateTemplate, AdminUpdateTemplate, SelectionTemplate,
    ConfirmationTemplate, CreateEntityTemplate, CustomTemplate,
    ButtonMenuTemplate, SearchTemplate, CheckboxSelectionTemplate
)
from PySide6.QtCore import QDate, Qt


def create_offense_update_template(
    update_handler: Callable,
    undo_handler: Callable,
    view_handler: Callable,
    enablement_check: Optional[Callable] = None
) -> Dict[str, Any]:
    """Create template for offense stat update dialog."""
    options = ["hit", "bb", "hbp", "so", "put out", "hr", "rbi", "runs", 
               "singles", "doubles", "triples", "sac fly", "fielder's choice"]
    
    return StatUpdateTemplate.create_template(
        title="Update Offense",
        stat_options=options,
        default_stat="hit",
        update_handler=update_handler,
        undo_handler=undo_handler,
        view_handler=view_handler,
        enablement_check=enablement_check,
        input_label="Enter value:",
        input_validator="positive_integer"
    )


def create_pitching_update_template(
    update_handler: Callable,
    undo_handler: Callable,
    view_handler: Callable,
    enablement_check: Optional[Callable] = None
) -> Dict[str, Any]:
    """Create template for pitching stat update dialog."""
    options = ["games played", "wins", "losses", "games started", "games completed", 
               "shutouts", "saves", "save opportunities", "IP", "at bats", "hits", 
               "runs", "ER", "HR", "HB", "walks", "SO"]
    
    return StatUpdateTemplate.create_template(
        title="Update Pitching",
        stat_options=options,
        default_stat="games played",
        update_handler=update_handler,
        undo_handler=undo_handler,
        view_handler=view_handler,
        enablement_check=enablement_check,
        input_label="Enter value:",
        input_validator="positive_integer"
    )


def create_team_stats_update_template(
    update_handler: Callable,
    undo_handler: Callable,
    view_handler: Callable,
    enablement_check: Optional[Callable] = None
) -> Dict[str, Any]:
    """Create template for team stats update dialog."""
    options = ["games played", "wins", "losses"]
    
    return StatUpdateTemplate.create_template(
        title="Update Team Stats",
        stat_options=options,
        default_stat="games played",
        update_handler=update_handler,
        undo_handler=undo_handler,
        view_handler=view_handler,
        enablement_check=enablement_check,
        input_label="Enter value:",
        input_validator="positive_integer"
    )


def create_admin_update_template(
    update_handler: Callable,
    undo_handler: Callable,
    toggle_handler: Optional[Callable] = None
) -> Dict[str, Any]:
    """Create template for team admin update dialog."""
    options = ["manager", "lineup", "positions", "max roster"]
    
    return AdminUpdateTemplate.create_template(
        title="Update Management",
        options=options,
        default_option=None,
        update_handler=update_handler,
        undo_handler=undo_handler,
        toggle_handler=toggle_handler,
        input_label="Enter value:",
        input_validator=None  # Text input, but can be validated per option
    )


def create_lineup_update_template(
    update_handler: Callable,
    undo_handler: Callable,
    toggle_handler: Optional[Callable] = None
) -> Dict[str, Any]:
    """Create template for lineup update dialog."""
    options = ["Leadoff", "2", "Three Hole", "Cleanup", "5", "6", "7", "8", "9", "custom"]
    
    template = SelectionTemplate.create_template(
        title="Update Lineup",
        selection_options=options,
        input_label="Enter Player:",
        default_option=None,
        update_handler=update_handler,
        undo_handler=undo_handler,
        toggle_handler=toggle_handler
    )
    
    # Add custom input for custom order
    template['custom_input'] = {
        'key': 'custom_order',
        'label': '',
        'type': 'text',
        'width': 35,
        'visible': False,
        'alignment': 'center'
    }
    
    return template


def create_positions_update_template(
    update_handler: Callable,
    undo_handler: Callable
) -> Dict[str, Any]:
    """Create template for positions update dialog."""
    options = ["pitcher", "catcher", "first base", "second base", "third base", 
               "shortstop", "left field", "center field", "right field"]
    
    return SelectionTemplate.create_template(
        title="Update Positions",
        selection_options=options,
        input_label="Enter Player:",
        default_option=None,
        update_handler=update_handler,
        undo_handler=undo_handler
    )


def create_remove_template(
    submit_handler: Callable
) -> Dict[str, Any]:
    """Create template for remove dialog."""
    options = ["League", "Current View"]
    
    return ConfirmationTemplate.create_template(
        title="Remove Item",
        options=options,
        default_option="Current View",
        submit_handler=submit_handler,
        submit_label="Submit"
    )


def create_theme_update_template(
    submit_handler: Callable
) -> Dict[str, Any]:
    """Create template for theme update dialog."""
    options = ["Light", "Dark"]  # Available theme options
    
    template = CustomTemplate.create_template(
        title="Update Theme",
        size=(400, 300),
        layout='standard',
        selection={
            'type': 'radio',
            'group_key': 'selection',
            'options': options,
            'default': options[0] if options else None,
            'enablement_logic': True  # All theme options should be enabled from the start
        },
        buttons={
            'submit': {
                'label': 'Submit',
                'width': 125,
                'handler': submit_handler
            }
        },
        button_layout='vertical'
    )
    
    return template


def create_search_template(
    search_handler: Callable,
    view_handler: Callable,
    clear_handler: Callable
) -> Dict[str, Any]:
    """Create template for search dialog."""
    options = ["player", "team", "number"]
    
    return SearchTemplate.create_template(
        title="Search Team or Player",
        search_options=options,
        search_handler=search_handler,
        view_handler=view_handler,
        clear_handler=clear_handler,
        input_label="Enter value:"
    )


def create_bar_graph_template(
    submit_handler: Callable
) -> Dict[str, Any]:
    """Create template for bar graph team selection dialog."""
    # Options will be populated dynamically from league
    return CheckboxSelectionTemplate.create_template(
        title="Select Teams for Graph",
        checkbox_options=[],  # Will be populated in custom_setup
        submit_handler=submit_handler,
        max_selections=6
    )


def create_league_update_template(
    update_handler: Callable,
    launch_handler: Callable,
    close_handler: Callable
) -> Dict[str, Any]:
    """Create template for league update dialog (custom due to date picker)."""
    options = ["Name", "Commissioner", "Historian", "Treasurer", "Recruitment", 
               "Communications", "Theme"]
    
    curr = QDate.currentDate()
    d = curr.day()
    m = curr.month()
    y = curr.year() - 1
    max_date = curr.addDays(365)
    
    template = CustomTemplate.create_template(
        title="Update League",
        size=(500, 400),
        layout='standard',
        inputs={
            'label': "Enter Admin:",
            'type': 'text',
            'alignment': Qt.AlignCenter
        },
        selection={
            'type': 'radio',
            'group_key': 'admin',
            'options': options,
            'default': 'Name',
            'toggle_handler': None  # Will be set in custom_setup
        },
        custom_widgets={
            'date_combo': {
                'type': 'combo_box',
                'items': ['Select...', 'Season Start', 'Season End'],
                'enabled': False,
                'layout': 'none',  # Will be manually added to date layout
                'activated_handler': None,  # Will be set in custom_setup
                'text_changed_handler': None  # Will be set in custom_setup
            },
            'date_edit': {
                'type': 'date_edit',
                'min_date': QDate(y, m, d),
                'max_date': max_date,
                'default_date': curr,
                'calendar_popup': True,
                'layout': 'none',  # Will be manually added to date layout
                'date_changed_handler': None  # Will be set in custom_setup
            }
        },
        buttons={
            'submit': {
                'label': 'Submit',
                'width': 150,
                'handler': update_handler
            },
            'launch': {
                'label': 'Launch',
                'width': 150,
                'handler': launch_handler
            }
        },
        close_handler=close_handler
    )
    
    return template


def create_hub_dialog_template(
    buttons: List[Dict[str, Any]],
    title: str = "Update Dialog"
) -> Dict[str, Any]:
    """Create template for hub/menu dialog."""
    return ButtonMenuTemplate.create_template(
        title=title,
        buttons=buttons,
        size=(400, 300)
    )

