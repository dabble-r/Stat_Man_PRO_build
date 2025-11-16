# Logic for UpdatePositionsDialog (pure functions, no Qt types)

from typing import Optional, Tuple, Callable
from src.core.team import Team
from src.core.player import Player
from src.core.linked_list import LinkedList
from src.core.stack import Stack
from PySide6.QtWidgets import QLineEdit, QWidget 
from src.ui.dialogs.message import Message

# --------------------------------------------------

def set_positions_team(pos: str, player: Player, team: Team, self: QWidget):
        """Apply the given position to team using team.set_pos with confirmation prompts."""
        '''"pitcher", "catcher", "first base", "second base", "third base", "shortstop", "left field", "center field", "right field"'''
        match pos:
            case 'pitcher':
                team.set_pos('positions', pos, player, self)
            case 'catcher':
                team.set_pos('positions', pos, player, self)
            case 'first base':
                team.set_pos('positions', pos, player, self)
            case 'second base':
                team.set_pos('positions', pos, player, self)
            case 'third base':
                team.set_pos('positions', pos, player, self)
            case 'shortstop':
                team.set_pos('positions', pos, player, self)
            case 'left field':
                team.set_pos('positions', pos, player, self)
            case 'center field':
                team.set_pos('positions', pos, player, self)
            case 'right field':
                team.set_pos('positions', pos, player, self)

# --------------------------------------------------

def update_stats(selected: Tuple[str, int], pos: str, player_input: str,
                 stack: Stack, message_instance: Message, league_instance: LinkedList, 
                 self: QWidget) -> None:
        """Validate inputs, push to undo stack, and update team position assignment."""
        player = player_input
        team, avg = selected
        find_team = league_instance.find_team(team)

        if not pos or not player:
            #QMessageBox.warning(self, "Input Error", "Enter player name and select position.")
            message_instance.show_message("Enter player name and select position.", btns_flag=False, timeout_ms=2000)
            return 
     
        ##print('team before:', find_team)

        # stack add node 
        # new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
        stack.add_node(find_team, team, 'positions', (pos, find_team.positions[pos]), set_positions_team, 'team')

        set_positions_team(pos, player, find_team, self)

        ##print('team after:', find_team.return_stats())

        ###print('team after:', find_team)