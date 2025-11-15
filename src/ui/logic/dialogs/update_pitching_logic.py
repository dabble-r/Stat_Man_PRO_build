"""Logic functions for pitching stat update dialog."""
from typing import Iterable, Dict, Callable, Any, Tuple
from src.core.stack import Stack
from src.core.linked_list import LinkedList
from src.core.player import Player
from src.core.team import Team
from src.ui.dialogs.message import Message
from src.utils.undo import Undo
from PySide6.QtWidgets import QDialog, QVBoxLayout
from src.ui.dialogs.stat_dialog_ui import Ui_StatDialog

# custom exception class for pitcher stat update errors
class PitcherStatUpdateError(Exception):
    """Raised when a pitcher stat update fails due to validation logic."""
    pass


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


def set_new_stat_pitcher(stat: str, val: int, player: Player) -> None:
    """Route chosen pitching stat to the matching setter on the player instance.
    
    Raises PitcherStatUpdateError if the setter fails to update due to validation.
    
    Args:
        stat: Human-readable stat label (e.g., 'wins', 'games played', 'IP')
        val: Integer value to set/add to the stat
        player: Player instance to update
        
    Raises:
        PitcherStatUpdateError: If the setter fails validation and doesn't update the stat
    """
    
    setter = PITCHER_SETTERS.get(stat)
    if not setter:
        raise PitcherStatUpdateError(f"Unknown stat: {stat}")
    
    # Store the value before update to detect if it changed
    attr_name = STAT_TO_ATTR_NAME.get(stat, stat.replace(" ", "_"))
    old_value = getattr(player, attr_name, 0)
    
    # Call the setter
    setter(player, val)
    
    # Check if the value actually changed (detect silent failures)
    new_value = getattr(player, attr_name, 0)
    
    # If value didn't change and we expected it to, the setter failed validation
    if old_value == new_value and val != 0:
        raise PitcherStatUpdateError(f"Failed to update {stat}: validation failed")

def build_pitching_undo_payload(stat_label: str) -> str:
    """Map human-readable stat label to internal attribute name for undo stack."""
    return STAT_TO_ATTR_NAME.get(stat_label, stat_label.replace(" ", "_"))

def reformat_stack_stat(stat):
    """Map human-readable stat label to the internal attribute name used in stack."""
    return build_pitching_undo_payload(stat)


def refresh_pitcher_derived_stats(player, team) -> None:
    """Recalculate all derived pitching stats and team ERA after stat updates."""
    player.set_era()
    player.set_WHIP()
    player.set_p_avg()
    player.set_k_9()
    player.set_bb_9()
    team.set_team_era()

def update_stats(selected: Tuple[str, str, int], stat: str, val: str, stack: Stack, message_instance: Message, 
                 league_instance: LinkedList, enable_buttons: Callable) -> None:
        """Validate selection and value, update pitcher stats, and push to the undo stack."""
        try:
            stat = stat
            val = int(val)
            if not stat or not val:
                message_instance.show_message("Must select a stat and enter value.", btns_flag=False, timeout_ms=2000)
                #QMessageBox.warning(self, "Input Error", "Must select a stat and enter value.")
                return
        except:
            message_instance.show_message("Must enter a number value to update stat.", btns_flag=False, timeout_ms=2000)
            #QMessageBox.warning(self, "Input Error", "Must enter a number value to update stat.")
            return

        player, team, num = selected
        find_team = league_instance.find_team(team)
        if not find_team:
            message_instance.show_message("Team not found.", btns_flag=False, timeout_ms=2000)
            return
        find_player = find_team.get_player(player)
        if not find_player:
            message_instance.show_message("Player not found.", btns_flag=False, timeout_ms=2000)
            return

        normalize_pitcher_numeric_fields(find_player, ['games_played', 'wins', 'losses', 'games_started', 'games_completed', 'shutouts', 'saves', 'save_ops', 'ip', 'p_at_bats', 'p_hits', 'p_runs', 'er', 'p_hr', 'p_hb', 'p_bb', 'p_so'])

        stat_stack = reformat_stack_stat(stat)
        stack.add_node(find_player, team, stat_stack, getattr(find_player, stat_stack), set_new_stat_pitcher, 'player')
        
        try: 
           # Apply the stat update
            set_new_stat_pitcher(stat, val, find_player)

             # Handle UI callback if needed
            if stat == 'games played':
                enable_buttons()

            refresh_pitcher_derived_stats(find_player, find_team)

        except:
            message_instance.show_message(f"Error updating pitching {stat}.", btns_flag=False, timeout_ms=2000)
           
       
def undo_stat(selected: Tuple[str, str, float], undo: Undo, league_instance: LinkedList, message_instance: Message) -> None:
    player, team, avg = selected

    find_team = league_instance.find_team(team)
    if find_team:
        find_player = find_team.get_player(player)
        if find_player:
            undo.undo_exp()
            refresh_pitcher_derived_stats(find_player, find_team)
        else:
            message_instance.show_message("Player not found.", btns_flag=False, timeout_ms=2000)
    else:
        message_instance.show_message("Team not found.", btns_flag=False, timeout_ms=2000)

def view_player_stats(selected: Tuple[str, str, float], league_instance: LinkedList, message_instance: Message, self) -> None:
    stat_widget = QDialog(self)
    stat_widget.setWindowTitle("Stats")
    stat_widget.setModal(True)
    #stat_layout = QVBoxLayout(stat_widget)

    stat_ui = Ui_StatDialog(league_instance, message_instance, selected, parent=stat_widget)
    stat_ui.get_stats(selected)
    stat_ui.exec()