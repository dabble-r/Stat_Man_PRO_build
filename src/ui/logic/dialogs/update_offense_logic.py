from email import message
from typing import Iterable, Callable, Optional, List, Tuple, Any, Union
import random
from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt

# --------------------------------------------------

def enforce_positive_integer(value, message) -> int:
    """Return integer value; tolerate strings/floats (0.0)/None by returning 0 on failure."""
    print('value:', value)
    try:
        if isinstance(value, str):
            print("string")
            if int(value) > 0:
                return int(value)
            else:
                message.show_message("Invalid value. Please enter a positive number without decimals.", btns_flag=False, timeout_ms=2000)
                return 0
    except Exception:
        print("Invalid value. Expected string for player offense stat.")
        return 0

# --------------------------------------------------

def coerce_at_bat(value) -> int:
    """Return integer at_bat value; tolerate strings/floats (0.0)/None by returning 0 on failure."""
    try:
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        s = str(value).strip()
        if s == "":
            return 0
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return 0

# --------------------------------------------------

def should_enable_buttons(at_bat_int: int) -> bool:
    """Return True if offense radios beyond 'hit' should be enabled (has ABs)."""
    return at_bat_int > 0

# --------------------------------------------------

def normalize_numeric_fields(obj, fields: Iterable[str]) -> None:
    """Coerce listed numeric attributes on obj to ints in-place to ensure arithmetic safety."""
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
                # leave as-is if coercion fails
                pass


OFFENSE_SETTERS: dict[str, Callable[[Any, int], None]] = {
    'hit': lambda p, v: p.set_hit(v),
    'bb': lambda p, v: p.set_bb(v),
    'hbp': lambda p, v: p.set_hbp(v),
    'put_out': lambda p, v: p.set_put_out(v),
    'so': lambda p, v: p.set_so(v),
    'hr': lambda p, v: p.set_hr(v),
    'rbi': lambda p, v: p.set_rbi(v),
    'runs': lambda p, v: p.set_runs(v),
    'singles': lambda p, v: p.set_singles(v),
    'doubles': lambda p, v: p.set_doubles(v),
    'triples': lambda p, v: p.set_triples(v),
    'sac_fly': lambda p, v: p.set_sac_fly(v),
    "fielder's choice": lambda p, v: p.set_fielder_choice(v),
}


def set_new_stat_player(stat: str, val: int, player, enable_buttons_callback: Optional[Callable[[], None]] = None) -> None:
    """Route chosen offense stat to the matching setter on the player instance."""
    setter = OFFENSE_SETTERS.get(stat)
    if setter:
        setter(player, val)
        if stat == 'hit' and enable_buttons_callback:
            enable_buttons_callback()


def refresh_player(player) -> None:
    """Recalculate all derived offense stats after stat updates."""
    player.set_AVG()
    player.set_BABIP()
    player.set_SLG()
    player.set_ISO()
    player.set_OBP()


def refresh_team(team) -> None:
    """Recalculate team-level derived stats after updates."""
    team.set_wl_avg()
    team.set_bat_avg()


def rand_avg() -> str:
    """Deprecated: Generate random average value (0.100-1.000) as string."""
    rand = random.randint(100, 1000)
    rand /= 1000
    return str(rand)


def rand_wl() -> str:
    """Deprecated: Generate random W-L record as string."""
    w = random.randint(0, 100)
    l = 100 - w
    wl = w / 100
    ret = (w, l, wl)
    return str(ret)


def no_dups(team, leaderboard_avg: List[Tuple]) -> None:
    """Remove existing team entry from leaderboard list to avoid duplicates."""
    for el in leaderboard_avg:
        if el[0] == team.name:
            indx = leaderboard_avg.index(el)
            leaderboard_avg.pop(indx)
            break


def add_leaderboard_list(team_upd, lst: List[Tuple]) -> None:
    """Append team entry (name, roster, avg) to leaderboard list."""
    name = team_upd.name
    roster = team_upd.max_roster
    avg = team_upd.get_bat_avg()
    lst.append((name, roster, avg))


def my_sort(x: Tuple) -> Any:
    """Sort key function for leaderboard sorting by average (third element)."""
    return x[2]


def sort_leaderboard(lst: List[Tuple]) -> List[Tuple]:
    """Sort leaderboard list by average using my_sort as key."""
    lst.sort(key=my_sort)
    return lst


def stat_lst(stat: str, val: int) -> Union[List, str]:
    """Build stat update list for complex stats; returns list or plain stat string."""
    def check(s: str) -> bool:
        lst = ["hit", "bb", "hbp", "so", "put out", "sac fly", "fielder's choice"]
        return s in lst
    
    one = ["pa"]
    two = ["pa", "at_bat"]
    if check(stat):
        if stat == "hit":
            two += [val, "hit"]
            return two
        elif stat == "bb":
            one += [val, "bb"]
            return one
        elif stat == "hbp":
            one += [val, "hbp"]
            return one
        elif stat == "so":
            two += [val, "so"]
            return two
        elif stat == "sac fly":
            two += [val, "sac_fly"]
            return two
        elif stat == "fielder's choice":
            two += [val, "fielder_choice"]
            return two
        elif stat == "put out":
            two += [val, "put_out"]
            return two
    
    return stat


def build_offense_undo_payload(stat_result: Union[List, str]) -> str:
    """Extract stat type from stat_lst result for undo stack payload."""
    return stat_result[-1] if isinstance(stat_result, list) else stat_result


def refresh_leaderboard_logic(league, team_upd, leaderboard_avg: List[Tuple]) -> List[Tuple]:
    """Update leaderboard list: remove duplicates, add team, sort. Returns updated list."""
    leaderboard_avg.clear()
    leaderboard_avg.extend(league.get_all_avg())
    no_dups(team_upd, leaderboard_avg)
    add_leaderboard_list(team_upd, leaderboard_avg)
    sort_leaderboard(leaderboard_avg)
    return leaderboard_avg


def insert_widget(view, lst: List[Tuple]) -> None:
    """Populate tree widget with leaderboard entries from sorted list."""
    view.clear()
    for el in lst:
        item = QTreeWidgetItem([el[0], str(el[2])])
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setTextAlignment(1, Qt.AlignCenter)
        item.setTextAlignment(2, Qt.AlignCenter)
        view.insertTopLevelItem(0, item)


