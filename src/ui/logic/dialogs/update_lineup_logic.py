# Logic for UpdateLineupDialog (pure functions, no Qt types)

from typing import Optional, Tuple
from src.core.team import Team


def order_to_slot(order_label: str, custom_text: Optional[str]) -> Optional[str]:
    """Map human-readable order label to numeric slot string; use custom_text when 'custom'."""
    if not order_label:
        return None
    if order_label == 'custom':
        return str(custom_text).strip() if custom_text is not None else None
    mapping = {
        'Leadoff': '1',
        '2': '2',
        'Three Hole': '3',
        'Cleanup': '4',
        '5': '5',
        '6': '6',
        '7': '7',
        '8': '8',
        '9': '9',
    }
    return mapping.get(order_label, str(order_label))


def validate_custom_slot(slot_text: str, team_max_roster: int) -> None:
    """Raise ValueError if custom slot not in [10, team_max_roster]."""
    try:
        slot = int(slot_text)
    except Exception as exc:
        raise ValueError("Custom slot must be an integer.") from exc
    if slot <= 9 or slot > int(team_max_roster):
        raise ValueError("Must enter a number greater than 9 and less than or equal to team max roster.")


def build_undo_payload_for_lineup(team: Team, slot: str) -> Tuple[str, Optional[str]]:
    """Return (slot, previous_player_name) tuple for undo stack use."""
    prev_value = team.lineup.get(slot)
    return (slot, prev_value)


def apply_lineup_assignment(team: Team, slot: str, player_name: str, parent) -> None:
    """Apply lineup assignment via team.set_lineup with existing replace semantics."""
    team.set_lineup('lineup', slot, player_name, parent)
