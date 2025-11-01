from typing import Optional
from src.core.team import Team


def team_wl_text(team_obj: Team) -> str:
    """Return W-L average display text for a team."""
    return team_obj.get_wl_avg()


def team_avg_text(team_obj: Team) -> str:
    """Return AVG display text for a team."""
    return team_obj.get_bat_avg()


def team_logo_path(team_obj: Team) -> Optional[str]:
    """Return logo file path string if available; else None."""
    return team_obj.logo


