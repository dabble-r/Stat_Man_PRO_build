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

