"""Logic functions for team admin/management update dialog."""
from typing import Tuple, Callable
from src.core.team import Team
from src.ui.dialogs.message import Message
from PySide6.QtWidgets import QLineEdit

# --------------------------------------------------

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

# --------------------------------------------------


def update_stats(dialog, set_new_stat_team: Callable, normalize_stat_name_for_stack: Callable) -> None:
        """Validate selection/value and update the chosen admin stat (manager or max_roster). Lineup/positions are opened by the UI layer."""
        selected = dialog.selected
        get_team_stat = lambda: dialog.get_selected_option('admin')
        input = dialog.input_fields['input']
        message_instance = dialog.message
        league_instance = dialog.league
        stack_instance = dialog.stack
        undo_instance = dialog.undo

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
        
        # Lineup and positions are handled in dialog_handlers; we only handle manager and max_roster here
        if stat in ('lineup', 'positions'):
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

