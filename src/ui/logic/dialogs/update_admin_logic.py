"""Logic functions for team admin/management update dialog."""
from typing import Tuple


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

