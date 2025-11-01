from typing import Optional


def must_have_team_before_add(league) -> bool:
    """Return True if league has at least one team; else False."""
    try:
        return int(getattr(league, 'get_count')()) > 0
    except Exception:
        # fallback: truthiness
        return bool(getattr(league, 'head', None))


