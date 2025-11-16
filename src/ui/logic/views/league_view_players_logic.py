from typing import Optional


def must_have_team_before_add(league) -> bool:
    """Return True if league has at least one team; else False."""
    return len(league.teams) > 0


