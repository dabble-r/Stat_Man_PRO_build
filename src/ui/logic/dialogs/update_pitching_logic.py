"""Logic functions for pitching stat update dialog."""
from typing import Iterable, Dict, Callable, Any


def check_games_played_for_enablement(games_played) -> bool:
    """Return True if player has any games played to enable all radio buttons."""
    try:
        games_int = int(float(str(games_played).strip() or 0))
        return games_int > 0
    except Exception:
        return False


def normalize_pitcher_numeric_fields(obj, fields: Iterable[str]) -> None:
    """Coerce listed numeric attributes on pitcher obj to ints in-place for arithmetic safety."""
    for f in fields:
        if hasattr(obj, f):
            try:
                curr = getattr(obj, f)
                if curr is None:
                    setattr(obj, f, 0)
                elif isinstance(curr, int):
                    continue
                elif isinstance(curr, float):
                    setattr(obj, f, int(curr))
                else:
                    s = str(curr).strip()
                    if s == "":
                        setattr(obj, f, 0)
                    elif "." in s:
                        setattr(obj, f, int(float(s)))
                    else:
                        setattr(obj, f, int(s))
            except Exception:
                pass


PITCHER_SETTERS: Dict[str, Callable[[Any, int], None]] = {
    'wins': lambda p, v: p.set_wins(v),
    'losses': lambda p, v: p.set_losses(v),
    'games started': lambda p, v: p.set_games_started(v),
    'games completed': lambda p, v: p.set_games_completed(v),
    'games played': lambda p, v: p.set_games_played(v),
    'shutouts': lambda p, v: p.set_shutouts(v),
    'saves': lambda p, v: p.set_saves(v),
    'save opportunities': lambda p, v: p.set_save_ops(v),
    'at bats': lambda p, v: p.set_p_at_bats(v),
    'IP': lambda p, v: p.set_ip(v),
    'hits': lambda p, v: p.set_p_hits(v),
    'runs': lambda p, v: p.set_p_runs(v),
    'ER': lambda p, v: p.set_er(v),
    'HR': lambda p, v: p.set_p_hr(v),
    'HB': lambda p, v: p.set_p_hb(v),
    'walks': lambda p, v: p.set_p_bb(v),
    'SO': lambda p, v: p.set_p_so(v),
}


STAT_TO_ATTR_NAME: Dict[str, str] = {
    'wins': 'wins',
    'losses': 'losses',
    'games started': 'games_started',
    'games completed': 'games_completed',
    'games played': 'games_played',
    'shutouts': 'shutouts',
    'saves': 'saves',
    'save opportunities': 'save_ops',
    'at bats': 'p_at_bats',
    'IP': 'ip',
    'hits': 'p_hits',
    'runs': 'p_runs',
    'ER': 'er',
    'HR': 'p_hr',
    'HB': 'p_hb',
    'walks': 'p_bb',
    'SO': 'p_so',
}


def apply_pitching_update(player, stat_label: str, val: int) -> None:
    """Apply validated pitching stat update via the matching setter; no UI logic."""
    setter = PITCHER_SETTERS.get(stat_label)
    if setter:
        setter(player, val)


def build_pitching_undo_payload(stat_label: str) -> str:
    """Map human-readable stat label to internal attribute name for undo stack."""
    return STAT_TO_ATTR_NAME.get(stat_label, stat_label.replace(" ", "_"))


def refresh_pitcher_derived_stats(player, team) -> None:
    """Recalculate all derived pitching stats and team ERA after stat updates."""
    player.set_era()
    player.set_WHIP()
    player.set_p_avg()
    player.set_k_9()
    player.set_bb_9()
    team.set_team_era()

