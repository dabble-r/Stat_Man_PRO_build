"""Logic functions for team stats update dialog."""


def refresh_team_derived_stats(team) -> None:
    """Recalculate team-level derived stats after game stat updates."""
    team.set_wl_avg()


def update_leaderboard_wl_item(item, target_team_name: str, wl_avg_str: str) -> bool:
    """Update tree item if team name matches; returns True if updated."""
    if item.text(0) == target_team_name:
        item.setText(1, wl_avg_str)
        return True
    return False

