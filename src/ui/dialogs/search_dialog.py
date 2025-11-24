"""
Search dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_search_template
from src.ui.dialogs.dialog_handlers import (
    search_submit_handler,
    search_view_handler,
    search_clear_handler
)
from typing import Union
from src.core.player import Player
from src.core.team import Team
from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt


class SearchDialog(BaseDialog):
    """Dialog for searching teams or players."""
    
    def __init__(self, league, selected, stack, undo, message, parent=None):
        # Create template
        template = create_search_template(
            search_handler=search_submit_handler,
            view_handler=search_view_handler,
            clear_handler=search_clear_handler
        )
        
        # Create context
        context = {
            'league': league,
            'selected': None,  # Will be set when item is selected
            'leaderboard': None,
            'lv_teams': None,
            'stack': stack,
            'undo': undo,
            'message': message
        }
        
        # Initialize base dialog
        super().__init__(template, context, parent=parent)
        
        # Store search-specific state
        self.type = None
        
        # Attach search population method
        self._populate_search = self._do_populate_search
    
    def _do_populate_search(self, selection: str, search_text: str):
        """Populate search tree with results."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        if selection == "player":
            find_player = self.league.find_player(search_text)
            if find_player:
                self._dups_handler(find_player.name, player=find_player)
            else:
                self.show_validation_error("Player not found.")
                return
        
        elif selection == "team":
            find_team = self.league.find_team(search_text)
            if find_team:
                self._dups_handler(find_team.name, team=find_team)
            else:
                self.show_validation_error("Team not found.")
                return
        
        elif selection == "number":
            try:
                number = int(search_text)
            except ValueError:
                self.show_validation_error("Please enter a valid number.")
                return
            
            find_player_list = self.league.find_player_by_number(number)
            if len(find_player_list) > 0:
                self._dups_handler(find_player_list)
            else:
                self.show_validation_error("Player number not found.")
                return
    
    def _check_dups(self, target: str) -> bool:
        """Check if target already exists in search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return False
        
        for i in range(tree_widget.topLevelItemCount()):
            item = tree_widget.topLevelItem(i)
            if item.text(0) == target:
                return True
        return False
    
    def _permit_dups(self, target: Union[str, list]) -> Union[bool, None]:
        """Check and handle duplicates."""
        if isinstance(target, str) and self._check_dups(target):
            self.message.show_message(f"Search results for {target} already found.", btns_flag=True)
            if self.message.choice == "ok":
                return True
            elif self.message.choice == "no":
                return False
            else:
                return None
        elif isinstance(target, str) and not self._check_dups(target):
            return True
        elif isinstance(target, list):
            ret = []
            for el in target:
                if self._check_dups(el.name):
                    ret.append(el.name)
            if len(ret) > 0:
                self.message.show_message(f"Search results for\n {ret}\n already found.", btns_flag=True)
                if self.message.choice == "ok":
                    return True
                elif self.message.choice == "no":
                    return False
                elif self.message.choice == "cancel":
                    return None
            else:
                return True
        return True
    
    def _dups_handler(self, target: Union[str, list], player: Player = None, team: Team = None):
        """Handle duplicate checking and add items to tree."""
        ret = self._permit_dups(target)
        
        if ret == False:
            return False
        elif ret == None:
            tree_widget = self.get_custom_widget('search_tree')
            if tree_widget:
                tree_widget.clear()
                tree_widget.setVisible(False)
            self.resize(500, 350)
            return None
        elif ret == True:
            tree_widget = self.get_custom_widget('search_tree')
            if not tree_widget:
                return
            
            if player:
                self._add_item_player(player)
            elif team:
                self._add_item_team(team)
            elif isinstance(target, list):
                self._add_item_number(target)
    
    def _add_item_player(self, player: Player):
        """Add player to search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        tree_widget.setVisible(True)
        self.resize(500, 750)
        self.type = "player"
        
        player_name = player.name
        team = player.team.name
        avg = player.get_AVG()
        item = QTreeWidgetItem([player_name, team, str(avg)])
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setTextAlignment(1, Qt.AlignCenter)
        item.setTextAlignment(2, Qt.AlignCenter)
        # Ensure item is selectable and enabled
        item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        tree_widget.addTopLevelItem(item)
    
    def _add_item_team(self, team: Team):
        """Add team to search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        tree_widget.setVisible(True)
        self.resize(500, 750)
        self.type = "team"
        
        name = team.name
        avg = team.get_bat_avg()
        item = QTreeWidgetItem([name, str(avg)])
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setTextAlignment(1, Qt.AlignCenter)
        # Ensure item is selectable and enabled
        item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        tree_widget.addTopLevelItem(item)
    
    def _add_item_number(self, player_list: list):
        """Add multiple players to search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        tree_widget.setVisible(True)
        self.resize(500, 750)
        self.type = "number"
        
        for el in player_list:
            player_name = el.name
            team = el.team.name
            avg = el.get_AVG()
            item = QTreeWidgetItem([player_name, team, str(avg)])
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            # Ensure item is selectable and enabled
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            tree_widget.addTopLevelItem(item)
