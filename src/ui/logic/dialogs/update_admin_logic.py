"""Logic functions for team admin/management update dialog."""
from typing import Tuple, Callable
from src.core.team import Team
from src.ui.dialogs.message import Message
from src.core.linked_list import LinkedList
from src.core.stack import Stack
from PySide6.QtWidgets import QLineEdit

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
                    message_instance.show_message("Roster value must be an integer between 1 and 50!")
                    return False
                team.set_max_roster(val)
                return True

def update_stats(selected: Tuple[str, int], get_team_stat: Callable, update_lineup_handler: Callable, 
                update_positions_handler: Callable, input: QLineEdit, message_instance: Message, league_instance: LinkedList, 
                stack_instance: Stack, set_new_stat_team: Callable, normalize_stat_name_for_stack: Callable) -> None:

        """Validate selection/value and update the chosen admin stat or open sub-dialogs."""
        
        # Extract team name early for error handling
        team, avg = selected
        
        try:
            stat = get_team_stat()
            print('stat before:', stat)
            
            # if stat is lineup, exec lineup dialog pop up
            if stat == 'lineup':
                ##print('lineup selected')
                update_lineup_handler()
                return
            
            if stat == 'positions':
                ##print('positions selected')
                update_positions_handler()
                return

            updated_input = input.text()

            if not stat or not updated_input:
                raise ValueError("Must select stat and enter value.")
            
        except Exception as e:
            #print("Exception:", e)
            message_instance.show_message(f"{team} update not successful.")
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

        message_instance.show_message(f'Team {stat} successfully updated!')
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

