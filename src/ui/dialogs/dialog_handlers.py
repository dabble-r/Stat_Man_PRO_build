"""
Handler functions that bridge BaseDialog and business logic layer.
These functions are used as callbacks in dialog templates.
"""
from typing import Callable, Optional
from src.ui.logic.dialogs.update_offense_logic import (
    coerce_at_bat,
    should_enable_buttons,
    normalize_numeric_fields,
    set_new_stat_player as logic_set_new_stat_player,
    refresh_player as logic_refresh_player,
    refresh_team as logic_refresh_team,
    refresh_leaderboard_logic,
    insert_widget as logic_insert_widget,
    stat_lst as logic_stat_lst,
    build_offense_undo_payload,
    enforce_positive_integer
)
from src.ui.logic.dialogs.update_pitching_logic import (
    check_games_played_for_enablement,
    normalize_pitcher_numeric_fields,
    set_new_stat_pitcher,
    refresh_pitcher_derived_stats,
    update_stats as pitching_update_stats,
    undo_stat as pitching_undo_stat,
    view_player_stats as pitching_view_player_stats
)
from PySide6.QtWidgets import QDialog, QMessageBox, QApplication


# ============================================================================
# Offense Update Handlers
# ============================================================================

def create_offense_enablement_check(dialog):
    """Create enablement check function for offense dialog."""
    def check_enablement(option, dialog_instance):
        """Check if radio option should be enabled based on player stats."""
        if option == 'hit':
            return True
        
        player, team, avg = dialog_instance.selected
        find_team = dialog_instance.league.find_team(team)
        if find_team:
            find_player = find_team.get_player(player)
            if find_player:
                at_bat = coerce_at_bat(getattr(find_player, 'at_bat', 0))
                return should_enable_buttons(at_bat)
        return False
    
    return check_enablement


def offense_update_handler(dialog):
    """Handle offense stat update submission."""
    stat = dialog.get_selected_option('stats')
    val_str = dialog.get_input_value('input')
    
    if not stat:
        dialog.show_validation_error("Must select a player stat to update.")
        return
    
    if not val_str:
        dialog.show_validation_error("Please enter value and select stat.")
        return
    
    val = enforce_positive_integer(val_str, dialog.message)
    if val == 0:
        return
    
    player, team, avg = dialog.selected
    find_team = dialog.league.find_team(team)
    if not find_team:
        dialog.show_validation_error("Selected team is no longer available. Refresh and try again.")
        return
    
    find_player = find_team.get_player(player)
    if not find_player:
        dialog.show_validation_error("Selected player is no longer available. Refresh and try again.")
        return
    
    # Normalize numeric fields
    try:
        numeric_fields = ['pa', 'at_bat', 'fielder_choice', 'hit', 'bb', 'hbp', 'put_out', 
                         'so', 'hr', 'rbi', 'runs', 'singles', 'doubles', 'triples', 'sac_fly']
        normalize_numeric_fields(find_player, numeric_fields)
    except Exception:
        pass
    
    # Build stat result and undo payload
    stat_result = logic_stat_lst(stat, val)
    statType = build_offense_undo_payload(stat_result)
    
    # Add to undo stack
    dialog.stack.add_node(find_player, team, stat_result, getattr(find_player, statType), 
                         lambda s, v, p: logic_set_new_stat_player(s, v, p, enable_buttons_callback=dialog.enable_selection_options), 
                         'player')
    
    # Update stat
    logic_set_new_stat_player(statType, int(val), find_player, 
                              enable_buttons_callback=lambda: dialog.enable_selection_options('stats', True))
    
    # Refresh derived stats
    logic_refresh_player(find_player)
    dialog.leaderboard.refresh_leaderboard(find_player)
    find_team.set_bat_avg()
    
    # Refresh leaderboard view
    leaderboard_avg = []
    refresh_leaderboard_logic(dialog.league, find_team, leaderboard_avg)
    logic_insert_widget(dialog.lv_teams.tree2_bottom, leaderboard_avg)
    
    # Clear input
    dialog.input_fields['input'].clear()


def offense_undo_handler(dialog):
    """Handle offense stat undo."""
    player, team, avg = dialog.selected
    find_team = dialog.league.find_team(team)
    if find_team:
        find_player = find_team.get_player(player)
        if find_player:
            dialog.undo.undo_exp(dialog.message)
            logic_refresh_player(find_player)
            logic_refresh_team(find_team)
            dialog.leaderboard.refresh_leaderboard(find_player)
            
            # Refresh leaderboard view
            leaderboard_avg = []
            refresh_leaderboard_logic(dialog.league, find_team, leaderboard_avg)
            logic_insert_widget(dialog.lv_teams.tree2_bottom, leaderboard_avg)


def offense_view_handler(dialog):
    """Handle view player stats."""
    # Lazy import to avoid circular dependency
    from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog
    
    stat_widget = QDialog(dialog)
    stat_widget.setWindowTitle("Stats")
    stat_widget.setModal(True)
    
    stat_ui = Ui_StatDialog(dialog.league, dialog.message, dialog.selected, parent=stat_widget)
    stat_ui.get_stats(dialog.selected)
    stat_ui.exec()


# ============================================================================
# Pitching Update Handlers
# ============================================================================

def create_pitching_enablement_check(dialog):
    """Create enablement check function for pitching dialog."""
    def check_enablement(option, dialog_instance):
        """Check if radio option should be enabled based on games played."""
        if option == 'games played':
            return True
        
        player, team, num = dialog_instance.selected
        find_team = dialog_instance.league.find_team(team)
        if find_team:
            find_player = find_team.get_player(player)
            if find_player:
                return check_games_played_for_enablement(find_player.games_played)
        return False
    
    return check_enablement


def pitching_update_handler(dialog):
    """Handle pitching stat update submission."""
    stat = dialog.get_selected_option('stats')
    val_str = dialog.get_input_value('input')
    
    if not stat or not val_str:
        dialog.show_validation_error("Must select a stat and enter value.")
        return
    
    # Use the logic layer function
    enable_buttons_callback = lambda: dialog.enable_selection_options('stats', True)
    
    if pitching_update_stats(dialog.selected, stat, val_str, dialog.stack, dialog.message, 
                            dialog.league, enable_buttons_callback):
        dialog.input_fields['input'].clear()


def pitching_undo_handler(dialog):
    """Handle pitching stat undo."""
    pitching_undo_stat(dialog.selected, dialog.undo, dialog.league, dialog.message)


def pitching_view_handler(dialog):
    """Handle view player stats."""
    pitching_view_player_stats(dialog.selected, dialog.league, dialog.message, dialog)


# ============================================================================
# Team Stats Update Handlers
# ============================================================================

def create_team_stats_enablement_check(dialog):
    """Create enablement check function for team stats dialog."""
    def check_enablement(option, dialog_instance):
        """Check if radio option should be enabled based on games played."""
        if option == 'games played':
            return True
        
        team, avg = dialog_instance.selected
        find_team = dialog_instance.league.find_team(team)
        if find_team:
            return find_team.games_played > 0
        return False
    
    return check_enablement


def team_stats_update_handler(dialog):
    """Handle team stats update submission."""
    stat = dialog.get_selected_option('stats')
    val_str = dialog.get_input_value('input')
    
    if not stat or not val_str:
        dialog.show_validation_error("Enter value and select stat.")
        return
    
    try:
        val = int(val_str)
    except ValueError:
        dialog.show_validation_error("Enter value and select stat.")
        return
    
    team, avg = dialog.selected
    find_team = dialog.league.find_team(team)
    if not find_team:
        dialog.show_validation_error("Team not found.")
        return
    
    # Normalize stat name for stack
    stat_stack = stat.replace(" ", "_")
    
    # Helper function to set team stat
    def set_team_stat(stat_name, val, team_obj):
        match stat_name:
            case 'wins':
                team_obj.set_wins(val, dialog)
            case 'losses':
                team_obj.set_losses(val, dialog)
            case 'games_played':
                team_obj.set_games_played(val, dialog)
                dialog.enable_selection_options('stats', True)
    
    # Add to undo stack
    dialog.stack.add_node(find_team, team, stat_stack, getattr(find_team, stat_stack), 
                         set_team_stat, 'team')
    
    # Update stat
    set_team_stat(stat, val, find_team)
    
    # Refresh derived stats
    from src.ui.logic.dialogs.update_team_stats_logic import refresh_team_derived_stats, update_leaderboard_wl_item
    refresh_team_derived_stats(find_team)
    
    # Update leaderboard
    count = dialog.lv_teams.tree1_bottom.topLevelItemCount()
    team_target = find_team.name
    wl_upd = find_team.get_wl_avg()
    for i in range(count):
        item = dialog.lv_teams.tree1_bottom.topLevelItem(i)
        if update_leaderboard_wl_item(item, team_target, wl_upd):
            break
    
    dialog.input_fields['input'].clear()


def team_stats_undo_handler(dialog):
    """Handle team stats undo."""
    team, avg = dialog.selected
    find_team = dialog.league.find_team(team)
    if find_team:
        dialog.undo.undo_exp()
        from src.ui.logic.dialogs.update_team_stats_logic import refresh_team_derived_stats, update_leaderboard_wl_item
        refresh_team_derived_stats(find_team)
        
        # Update leaderboard
        count = dialog.lv_teams.tree1_bottom.topLevelItemCount()
        team_target = find_team.name
        wl_upd = find_team.get_wl_avg()
        for i in range(count):
            item = dialog.lv_teams.tree1_bottom.topLevelItem(i)
            if update_leaderboard_wl_item(item, team_target, wl_upd):
                break


def team_stats_view_handler(dialog):
    """Handle view team stats."""
    # Lazy import to avoid circular dependency
    from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog
    
    stat_widget = QDialog(dialog)
    stat_widget.setWindowTitle("Stats")
    stat_widget.setModal(True)
    
    stat_ui = Ui_StatDialog(dialog.league, dialog.message, dialog.selected, parent=stat_widget)
    stat_ui.get_stats(dialog.selected)
    stat_ui.exec()


# ============================================================================
# Admin Update Handlers
# ============================================================================

def admin_toggle_handler(option, checked, dialog):
    """Handle admin option toggle to show/hide input field."""
    if checked:
        if option in ['lineup', 'positions']:
            dialog.input_fields['input'].setVisible(False)
        elif option == 'max roster':
            from PySide6.QtGui import QIntValidator
            dialog.input_fields['input'].setValidator(QIntValidator(1, 50))
            dialog.input_fields['input'].setVisible(True)
        else:
            dialog.input_fields['input'].setValidator(None)
            dialog.input_fields['input'].setVisible(True)


def admin_update_handler(dialog):
    """Handle admin update submission."""
    from src.ui.logic.dialogs.update_admin_logic import (
        update_stats as admin_update_stats,
        set_new_stat_team,
        normalize_stat_name_for_stack,
        update_lineup_handler,
        update_positions_handler
    )
    
    stat = dialog.get_selected_option('admin')
    input_value = dialog.get_input_value('input')
    
    if not stat:
        dialog.show_validation_error("Please select a stat option (manager, lineup, positions, or max roster).")
        return
    
    # Create wrapper functions for lineup and positions handlers
    def lineup_wrapper(league_instance, selected, leaderboard_instance, lv_teams_instance, 
                      stack_instance, undo_instance, message_instance, parent=None):
        from src.ui.dialogs.update_lineup import UpdateLineupDialog
        lineup_dialog = UpdateLineupDialog(league_instance, selected, leaderboard_instance, 
                                          lv_teams_instance, stack_instance, undo_instance, 
                                          message_instance, parent=parent)
        lineup_dialog.exec()
    
    def positions_wrapper(league_instance, selected, leaderboard_instance, lv_teams_instance, 
                         stack_instance, undo_instance, message_instance, parent=None):
        from src.ui.dialogs.update_positions import UpdatePositionsDialog
        positions_dialog = UpdatePositionsDialog(league_instance, selected, leaderboard_instance, 
                                                lv_teams_instance, stack_instance, undo_instance, 
                                                message_instance, parent=parent)
        positions_dialog.exec()
    
    # Use the logic layer function
    admin_update_stats(
        dialog.selected,
        lambda: stat,
        lineup_wrapper,
        positions_wrapper,
        dialog.input_fields['input'],
        dialog.message,
        dialog.league,
        dialog.stack,
        dialog.undo,
        dialog.leaderboard,
        dialog.lv_teams,
        set_new_stat_team,
        normalize_stat_name_for_stack,
        parent=dialog
    )


def admin_undo_handler(dialog):
    """Handle admin update undo."""
    dialog.undo.undo_exp()


# ============================================================================
# Lineup Update Handlers
# ============================================================================

def lineup_toggle_handler(option, checked, dialog):
    """Handle lineup option toggle to show/hide custom input."""
    if checked and option == 'custom':
        dialog.set_custom_input_visible('custom_order', True)
    else:
        dialog.set_custom_input_visible('custom_order', False)


def lineup_update_handler(dialog):
    """Handle lineup update submission."""
    from src.ui.logic.dialogs.update_lineup_logic import (
        update_stats as lineup_update_stats,
        order_to_slot,
        apply_lineup_assignment
    )
    
    order_label = dialog.get_selected_option('selection')
    player = dialog.get_input_value('input')
    custom_order = dialog.get_custom_input_value('custom_order')
    
    if not order_label or not player:
        dialog.show_validation_error("Enter player name and select batting order.")
        return
    
    # Create delegate function
    def apply_delegate(order, player_name, team_obj):
        slot = order_to_slot(order, custom_order if order == 'custom' else None)
        apply_lineup_assignment(team_obj, slot, player_name, dialog)
    
    # Use the logic layer function
    lineup_update_stats(
        order_label,
        player,
        dialog.stack,
        dialog.message,
        dialog.input_fields.get('custom_order'),
        dialog.league,
        dialog.selected,
        apply_delegate
    )
    
    dialog.input_fields['input'].clear()
    if 'custom_order' in dialog.input_fields:
        dialog.input_fields['custom_order'].clear()


def lineup_undo_handler(dialog):
    """Handle lineup update undo."""
    dialog.undo.undo_exp()


# ============================================================================
# Positions Update Handlers
# ============================================================================

def positions_update_handler(dialog):
    """Handle positions update submission."""
    from src.ui.logic.dialogs.update_positions_logic import (
        update_stats as positions_update_stats,
        set_positions_team
    )
    
    pos = dialog.get_selected_option('selection')
    player_input = dialog.get_input_value('input')
    
    if not pos or not player_input:
        dialog.show_validation_error("Enter player name and select position.")
        return
    
    # Use the logic layer function
    positions_update_stats(
        dialog.selected,
        pos,
        player_input,
        dialog.stack,
        dialog.message,
        dialog.league,
        dialog
    )
    
    dialog.message.show_message("Position successfully updated!", btns_flag=False, timeout_ms=2000)
    dialog.input_fields['input'].clear()


def positions_undo_handler(dialog):
    """Handle positions update undo."""
    dialog.undo.undo_exp()


# ============================================================================
# Theme Update Handlers
# ============================================================================

def theme_submit_handler(dialog):
    """Handle theme selection submission."""
    from PySide6.QtWidgets import QApplication
    
    selection = dialog.get_selected_option('selection')
    if not selection:
        return
    
    # Map theme selection to style method
    theme_map = {
        "Light": "light_styles",
        "Dark": "dark_styles",
        "default": "light_styles"  # Fallback
    }
    
    # Get styles from dialog (stored as self.styles in UpdateTheme)
    if not hasattr(dialog, 'styles') or dialog.styles is None:
        # If no styles object, try to get from QApplication
        app = QApplication.instance()
        if app:
            # Create new styles instance
            from src.ui.styles.stylesheets import StyleSheets
            styles = StyleSheets()
        else:
            dialog.close()
            return
    else:
        styles = dialog.styles
    
    # Get the style method name
    style_method = theme_map.get(selection, "light_styles")
    
    # Get the style string
    if hasattr(styles, style_method):
        style_func = getattr(styles, style_method)
        if callable(style_func):
            style_sheet = style_func()
        else:
            style_sheet = style_func
    else:
        # Fallback to light styles
        style_sheet = styles.get_monochrome_1_style()
    
    # Apply theme to QApplication (affects all widgets)
    app = QApplication.instance()
    if app:
        app.setStyleSheet(style_sheet)
    
    # Also apply to main window if found
    def get_ancestor(widget, obj_name):
        current = widget
        while current is not None:
            if hasattr(current, 'objectName') and current.objectName() == obj_name:
                return current
            current = current.parentWidget()
        return None
    
    main_window = get_ancestor(dialog, "Main Window")
    if main_window:
        main_window.setStyleSheet(style_sheet)
    
    # Enable parent controls if parent exists
    if hasattr(dialog, 'parent') and dialog.parent:
        if hasattr(dialog.parent, 'user_input'):
            dialog.parent.user_input.setEnabled(True)
        if hasattr(dialog.parent, 'date_combo'):
            dialog.parent.date_combo.setEnabled(True)
            dialog.parent.date_combo.setCurrentIndex(0)
    
    dialog.close()


# ============================================================================
# Search Dialog Handlers
# ============================================================================

def _normalize_search_selection(selection: Optional[str]) -> Optional[str]:
    """Map display label to internal option value for search type."""
    if selection == "Natural Language Query":
        return "nl_query"
    return selection


def search_toggle_handler(option: str, checked: bool, dialog):
    """Handle search type radio button toggle."""
    # Support both internal value and display label
    is_nl = (option == "nl_query" or option == "Natural Language Query")
    
    if checked and is_nl:
        try:
            from src.ui.dialogs.nl_query_dialog import NLQueryDialog
        except Exception as e:
            QMessageBox.warning(
                dialog,
                "Natural Language Query",
                f"Could not open Natural Language Query dialog:\n{e}\n\n"
                "Check that required packages are installed (e.g. when running from the built app)."
            )
            return
        try:
            if not hasattr(dialog, '_nl_dialog') or not dialog._nl_dialog:
                dialog._nl_dialog = NLQueryDialog(parent=dialog)
            dialog._nl_dialog.show()
            QApplication.processEvents()
            dialog._nl_dialog.raise_()
            dialog._nl_dialog.activateWindow()
        except Exception as e:
            QMessageBox.warning(
                dialog,
                "Natural Language Query",
                f"Could not show Natural Language Query dialog:\n{e}"
            )
    
    elif not checked and is_nl:
        # Hide NL dialog and stop servers when switching away
        if hasattr(dialog, '_nl_dialog') and dialog._nl_dialog:
            if hasattr(dialog._nl_dialog, 'server_manager') and dialog._nl_dialog.server_manager:
                dialog._nl_dialog.server_manager.stop_all_servers()
            dialog._nl_dialog.hide()


def search_submit_handler(dialog):
    """Handle search submission."""
    raw_selection = dialog.get_selected_option('search_type')
    selection = _normalize_search_selection(raw_selection)
    
    # Handle nl_query - show dialog instead of standard search
    if selection == "nl_query":
        if hasattr(dialog, '_nl_dialog') and dialog._nl_dialog:
            dialog._nl_dialog.show()
            QApplication.processEvents()
            dialog._nl_dialog.raise_()
            dialog._nl_dialog.activateWindow()
        else:
            dialog.show_validation_error(
                "Please select 'Natural Language Query' from the search type options to open the NL query dialog."
            )
        return
    
    # Standard search handling for player, team, number
    # Get search text
    search_text = dialog.get_input_value('input')
    
    if not selection:
        dialog.show_validation_error("Please select a search type.")
        return

    if not search_text:
        dialog.show_validation_error("Please enter a search value.")
        return

    # Setup tree widget based on selection
    tree_widget = dialog.get_custom_widget('search_tree')
    if tree_widget:
        if selection == "player" or selection == "number":
            tree_widget.setHeaderLabels(["Name", "Team", "Average"])
            tree_widget.setColumnCount(3)
        elif selection == "team":
            tree_widget.setHeaderLabels(["Team", "Average"])
            tree_widget.setColumnCount(2)
    
    # Populate search results
    if hasattr(dialog, '_populate_search'):
        dialog._populate_search(selection, search_text)
    dialog.input_fields['input'].clear()


def search_view_handler(dialog):
    """Handle view selected search result."""
    from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog
    from PySide6.QtWidgets import QDialog
    
    tree_widget = dialog.get_custom_widget('search_tree')
    if not tree_widget:
        dialog.show_validation_error("Search tree not available.")
        return
    
    # Try to get current item (selected item)
    current_item = tree_widget.currentItem()
    
    # If no current item, try to get selected items
    if not current_item:
        selected_items = tree_widget.selectedItems()
        if selected_items:
            current_item = selected_items[0]
    
    # If still no item, check if there's only one item and select it
    if not current_item and tree_widget.topLevelItemCount() == 1:
        current_item = tree_widget.topLevelItem(0)
        tree_widget.setCurrentItem(current_item)
    
    if not current_item:
        dialog.show_validation_error("Please select a team or player from the search results.")
        return
    
    # Build selected tuple based on type
    search_type = getattr(dialog, 'type', None)
    if search_type == "player" or search_type == "number":
        # Player/Number search has 3 columns: Name, Team, Average
        if current_item.columnCount() >= 3:
            dialog.selected = [current_item.text(0), current_item.text(1), current_item.text(2)]
        else:
            dialog.show_validation_error("Invalid player data in search results.")
            return
    elif search_type == "team":
        # Team search has 2 columns: Team, Average
        if current_item.columnCount() >= 2:
            dialog.selected = [current_item.text(0), current_item.text(1)]
        else:
            dialog.show_validation_error("Invalid team data in search results.")
            return
    elif search_type == "nl_query":
        # NL query results are generic SQL results - view action not applicable
        dialog.show_validation_error(
            "View action is not available for natural language query results. "
            "Results are displayed in the search tree."
        )
        return
    else:
        dialog.show_validation_error("Unknown search type.")
        return
    
    stat_widget = QDialog(dialog)
    stat_widget.setWindowTitle("Stats")
    stat_widget.setModal(True)
    
    stat_ui = Ui_StatDialog(dialog.league, dialog.message, dialog.selected, parent=stat_widget)
    stat_ui.get_stats(dialog.selected)
    stat_ui.exec()


def search_clear_handler(dialog):
    """Handle clear search results."""
    tree_widget = dialog.get_custom_widget('search_tree')
    if tree_widget:
        tree_widget.clear()
        tree_widget.setVisible(False)
    dialog.resize(500, 350)


# ============================================================================
# Bar Graph Dialog Handlers
# ============================================================================

def bar_graph_submit_handler(dialog):
    """Handle bar graph team selection submission."""
    selected_teams = dialog.get_selected_checkboxes('selection')
    
    if len(selected_teams) == 0:
        dialog.show_validation_error("Select at least one team.")
        return
    
    dialog.close()


# ============================================================================
# League Update Handlers
# ============================================================================

def league_update_handler(dialog):
    """Handle league update submission."""
    from PySide6.QtWidgets import QMessageBox
    
    if not hasattr(dialog, '_get_league_admin'):
        # Fallback if method not attached
        date_combo = dialog.get_custom_widget('date_combo')
        stat = dialog.get_selected_option('admin')
        if date_combo and date_combo.currentIndex() != 0:
            stat = date_combo.currentText()
    else:
        stat = dialog._get_league_admin()
    
    val = dialog.get_input_value('input')
    
    if 'Season' not in stat:
        if not stat or not val:
            QMessageBox.warning(dialog, "Input Error", "Enter player name and select admin position.")
            return
    elif 'Season' in stat:
        if not hasattr(dialog, 'new_date') or dialog.new_date is None:
            QMessageBox.warning(dialog, "Input Error", "Please select date and submit.")
            return
    
    if hasattr(dialog, '_set_admin_league'):
        dialog._set_admin_league(stat, val)
    else:
        # Fallback implementation
        if 'Season' in stat:
            if dialog.new_date:
                day, week, month, year = dialog.new_date
                dialog.league.set_admin('admin', stat, f"{month}--{day}--{year}", dialog)
        else:
            dialog.league.set_admin('admin', stat, val, dialog)
    
    if hasattr(dialog, '_on_submit'):
        dialog._on_submit()
    
    if hasattr(dialog, '_clear_all'):
        dialog._clear_all()
    else:
        if 'input' in dialog.input_fields:
            dialog.input_fields['input'].clear()


def league_launch_handler(dialog):
    """Handle league launch."""
    from PySide6.QtWidgets import QMessageBox
    
    league_name = getattr(dialog, 'league_name', False)
    
    if league_name is True:
        reply = QMessageBox.question(
            dialog,
            "Confirm Close",
            "Would you like to continue without customizing league?",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Ok:
            dialog.destroy()
        elif reply == QMessageBox.Cancel:
            return
    else:
        dialog.destroy()


def league_close_handler(event, dialog):
    """Handle league dialog close event."""
    from PySide6.QtWidgets import QMessageBox
    
    league_name = getattr(dialog, 'league_name', False)
    
    if league_name is False:
        event.accept()
    else:
        reply = QMessageBox.question(
            dialog,
            "Confirm Close",
            "Would you like to continue without customizing league?",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Ok:
            event.accept()
        elif reply == QMessageBox.Cancel:
            event.ignore()


# ============================================================================
# Remove Dialog Handlers
# ============================================================================

def remove_submit_handler(dialog):
    """Handle remove item submission."""
    from PySide6.QtWidgets import QMessageBox
    
    selection = dialog.get_selected_option('confirmation')
    
    if not dialog.league.teams:
        return
    
    if selection == "Current View":
        # Remove from visible views only
        if len(dialog.selected) == 2:
            team, avg = dialog.selected
            find_team = dialog.league.find_team(team)
            if find_team:
                dialog.lv_teams.remove_league_view_wl(find_team)
                dialog.lv_teams.remove_league_view_avg(find_team)
        elif len(dialog.selected) == 3:
            player, team, avg = dialog.selected
            find_team = dialog.league.find_team(team)
            if find_team:
                find_player = find_team.get_player(player)
                if find_player:
                    dialog.lv_players.remove_league_view(find_player)
                    dialog.leaderboard.remove_handler(find_player)
    
    elif selection == "League":
        # Remove from league after confirmation
        if len(dialog.selected) == 2:
            ques = QMessageBox(dialog)
            ques.setWindowTitle("Confirm Action")
            ques.setText("Do you want to remove team and all associated players?")
            ques.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            ques.setDefaultButton(QMessageBox.Cancel)
            
            result = ques.exec()
            if result == QMessageBox.Cancel:
                return
            
            team, avg = dialog.selected
            find_team = dialog.league.find_team(team)
            if find_team:
                dialog.lv_teams.remove_league_view_wl(find_team)
                dialog.lv_teams.remove_league_view_avg(find_team)
                
                team_players = find_team.players
                for el in team_players:
                    dialog.lv_players.remove_league_view(el)
                    dialog.leaderboard.refresh_leaderboard_removal(el)
                
                dialog.league.remove_team(team)
        
        elif len(dialog.selected) == 3:
            ques = QMessageBox(dialog)
            ques.setWindowTitle("Confirm Action")
            ques.setText("Do you want to remove player and all stats permanently?")
            ques.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            ques.setDefaultButton(QMessageBox.Cancel)
            
            result = ques.exec()
            if result == QMessageBox.Cancel:
                return
            
            player, team, avg = dialog.selected
            find_team = dialog.league.find_team(team)
            if find_team:
                find_player = find_team.get_player(player)
                if find_player:
                    find_team.remove_player(player)
                    dialog.lv_players.remove_league_view(find_player)
                    dialog.leaderboard.remove_handler(find_player)
    
    dialog.close()

