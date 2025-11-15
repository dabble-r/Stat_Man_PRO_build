"""Logic functions for team admin/management update dialog."""
from typing import Tuple, Callable
from src.core.team import Team
from src.ui.dialogs.message import Message
from src.core.linked_list import LinkedList
from src.core.stack import Stack
from PySide6.QtWidgets import QLineEdit
from src.ui.views.leaderboard_ui import Leaderboard
from src.ui.views.league_view_teams import LeagueViewTeams  
from PySide6.QtWidgets import QWidget
from src.utils.undo import Undo
from src.ui.dialogs.update_lineup import UpdateLineupDialog
from src.ui.dialogs.update_positions import UpdatePositionsDialog

def set_new_stat_team(stat: str, input: str, team: Team, message_instance: Message) -> bool:
        """Apply admin change to team: manager/lineup/positions/max_roster with validation."""
        val = None
        match stat:
            case 'manager':
                team.set_manager(input)
                return True
            case 'lineup':
                print('lineup selected')
            case 'positions':
                print("positions selected")
            case 'max_roster':
                is_valid, val = validate_roster_value(input)
                if not is_valid:
                    message_instance.show_message("Roster value must be an integer between 1 and 50!", btns_flag=False, timeout_ms=2000)
                    return False
                team.set_max_roster(val)
                return True

def update_lineup_handler(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=None):
        """Open lineup dialog to adjust batting order for the current team."""
        ##print('lineup handler called')
        dialog = UpdateLineupDialog(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=parent)
        dialog.exec()

def update_positions_handler(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=None):
        """Open positions dialog to adjust player positions for the current team."""
        ##print('positions handler called')
        dialog = UpdatePositionsDialog(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=parent)
        dialog.exec()

def update_stats(selected: Tuple[str, int], get_team_stat: Callable, update_lineup_handler: Callable, 
                update_positions_handler: Callable, input: QLineEdit, message_instance: Message, league_instance: LinkedList, 
                stack_instance: Stack, undo_instance: Undo, leaderboard_instance: Leaderboard, lv_teams_instance: LeagueViewTeams, set_new_stat_team: Callable, normalize_stat_name_for_stack: Callable, parent: QWidget) -> None:

        """Validate selection/value and update the chosen admin stat or open sub-dialogs."""
        
        # Extract team name early for error handling
        team, avg = selected
        
        # Try to get the selected stat from radio buttons
        try:
            stat = get_team_stat()
            print('stat before:', stat)
        except AttributeError:
            message_instance.show_message("Please select a stat option (manager, lineup, positions, or max roster).", btns_flag=False, timeout_ms=2000)
            return
        except Exception as e:
            message_instance.show_message(f"Error reading stat selection: {str(e)}", btns_flag=False, timeout_ms=2000)
            return
        
        # Handle lineup dialog
        if stat == 'lineup':
            try:
                update_lineup_handler(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=parent)
            except TypeError as e:
                message_instance.show_message(f"Lineup dialog error: Invalid arguments. {str(e)}", btns_flag=False, timeout_ms=2000)
                return
            except Exception as e:
                message_instance.show_message(f"Failed to open lineup dialog: {str(e)}", btns_flag=False, timeout_ms=2000)
                return
            return
        
        # Handle positions dialog
        if stat == 'positions':
            try:
                update_positions_handler(league_instance, selected, leaderboard_instance, lv_teams_instance, stack_instance, undo_instance, message_instance, parent=parent)
            except TypeError as e:
                message_instance.show_message(f"Positions dialog error: Invalid arguments. {str(e)}", btns_flag=False, timeout_ms=2000)
                return
            except Exception as e:
                message_instance.show_message(f"Failed to open positions dialog: {str(e)}", btns_flag=False, timeout_ms=2000)
                return
            return

        # Handle input-based stats (manager, max roster)
        try:
            updated_input = input.text()
            
            if not stat or not updated_input:
                raise ValueError("Must select stat and enter value.")
        except ValueError as e:
            message_instance.show_message(str(e), btns_flag=False, timeout_ms=2000)
            return
        except Exception as e:
            message_instance.show_message(f"Error reading input value: {str(e)}", btns_flag=False, timeout_ms=2000)
            return

        find_team = league_instance.find_team(team)

        ##print('team before:', find_team)

        # node - stack
        # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
        stat_stack = normalize_stat_name_for_stack(stat)

        # Pass function reference, not call it - store previous value before update
        stack_instance.add_node(find_team, team, stat_stack, getattr(find_team, stat_stack), set_new_stat_team, 'team')
        
        ##print('stat - update stats:', stat)
        # Now call the function to actually update the team
        set_new_stat_team(stat, updated_input, find_team, message_instance)

        message_instance.show_message(f'Team {stat} successfully updated!', btns_flag=False, timeout_ms=2000)
        #msg = show_message(self, f'Team {stat} successfully updated!')
        #msg.exec()

        input.clear()

        ##print('stack after:', self.stack)
        ##print('team after:', find_team)
                

def validate_roster_value(input_str: str) -> Tuple[bool, int]:
    """Validate and convert roster input to integer; returns (is_valid, value or 0)."""
    try:
        val = int(input_str.strip())
        if 1 <= val <= 50:
            return True, val
        return False, 0
    except Exception:
        return False, 0


def normalize_stat_name_for_stack(stat_label: str) -> str:
    """Convert display stat label to internal attribute name for undo stack."""
    if stat_label == 'max roster':
        return 'max_roster'
    return stat_label.replace(" ", "_")

