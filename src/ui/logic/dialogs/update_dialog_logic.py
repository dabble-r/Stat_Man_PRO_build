from typing import Iterable


def player_has_pitching(positions: Iterable[str]) -> bool:
    """Return True if 'pitcher' is present in the positions iterable."""
    try:
        return 'pitcher' in positions
    except Exception:
        return False


def set_team_logo(team_obj, file_path: str) -> None:
    """Assign logo file path to team object; no validation here."""
    team_obj.logo = file_path


def set_player_image(player_obj, file_path: str) -> None:
    """Assign image file path to player object; no validation here."""
    player_obj.image = file_path


