"""Logic functions for team admin/management update dialog."""
from typing import Tuple
from src.core.team import Team
from src.ui.dialogs.message import Message

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

def update_stats():
        """Validate selection/value and update the chosen admin stat or open sub-dialogs."""
        stat = None
        input = None
        team, num = self.selected
        try:
            stat = self.get_team_stat()
            ##print('stat before if:', stat)
            
            # if stat is lineup, exec lineup dialog pop up
            if stat == 'lineup':
                ##print('lineup selected')
                self.update_lineup_handler()
                return
            
            if stat == 'positions':
                ##print('positions selected')
                self.update_positions_handler()
                return

            input = self.input.text()

            if not stat or not input:
                raise ValueError("Must select stat and enter value.")
            
        except:
            ##print('Exception', e)
            #QMessageBox.warning(self, "Error", f"{stat} update not successful.")
            self.message.show_message(f"{team} update not successful.")
            return

        team, avg = self.selected
        find_team = self.league.find_team(team)

        ##print('team before:', find_team)

        # node - stack
        # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
        stat_stack = normalize_stat_name_for_stack(stat)

        self.stack.add_node(find_team, team, stat_stack, getattr(find_team, stat_stack), self.set_new_stat_team, 'team')
        
        ##print('stat - update stats:', stat)
        self.set_new_stat_team(stat, input, find_team)

        self.message.show_message(f'Team {stat} successfully updated!')
        #msg = show_message(self, f'Team {stat} successfully updated!')
        #msg.exec()

        self.input.clear()

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

