from src.core.player import Player
from PySide6.QtWidgets import QMessageBox
import math

# --------------------------------------------------

class Team:
    """Team entity holding roster, admin fields, and computed team statistics."""
    def __init__(self, league, name, manager, message=None, max_roster=math.inf):
        self.name = name
        self.league = league
        self.leagueID = self.league.leagueID
        self.teamID = self.get_hash()
        self.logo = None
        self.manager = manager
        self.players = []
        # generate empty list/dict of length determined by max_roster roster value
        self.lineup = {
            "1": None,
            "2": None,
            "3": None,
            "4": None,
            "5": None,
            "6": None,
            "7": None,
            "8": None,
            "9": None
        }
        self.positions = {
            'pitcher': None,
            'catcher': None,
            'first base': None,
            'second base': None,
            'third base': None,
            'shortstop': None,
            'left field': None,
            'center field': None,
            'right field': None
        }
        self.wins = 0
        self.losses = 0
        self.games_played = 0
        self.wl_avg = 0
        self.bat_avg = 0
        self.team_era = 0
        self.max_roster = max_roster

        # message instance
        self.message = message

    # ------------------------------------------------------------------------ #
    # utilities

    def __str__(self):
        ret = ''
        # print(self.players)
        ret += f'Team: {self.name}\nManager: {self.manager}\nRoster: {self.get_size()} / {self.max_roster}\nPlayers: {[x.name for x in self.players]}\nG: {self.games_played}\nWins: {self.wins}\nLosses: {self.losses}\nW-L: {self.wl_avg}\nAVG: {self.bat_avg}\nTeam Era: {self.team_era}'
        return ret

    def get_hash(self):
        """Return deterministic integer hash for teamID based on team name characters."""
        def indx(a, b):
            index = a.index(b)
            if index == 0:
                return 2
            return index
        ord_lst = [sum(ord(x) * indx(self.name, x) for x in self.name)]
        return ord_lst.pop()

    def less_zero(self, stat, val):
        return stat + val < 0

    def ques_replace(self, attr, stat, parent):
        existing_val = getattr(self, attr)[stat]
        if existing_val:
            reply = QMessageBox.question(parent, "Input Error", f"Would you like to replace {existing_val} at {stat}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            return reply
        return None

    def format_decimal(self, num):
        return "{:.3f}".format(num)

    def populate_lineup(self):
        """Extend lineup dict with numeric slots up to max_roster as None."""
        for indx in range(10, self.max_roster + 1):
            self.lineup[str(indx)] = None

    def _get_attrs(self):
        directory = dir(self)
        ret = []
        for el in directory:
            temp = getattr(self, el)
            if isinstance(temp, int):
                # print(temp, el)
                ret.append((el, temp))
        return ret

    def format_attrs_players(self):
        ret = []
        for el in self.players:
            directory = dir(el)
            temp = getattr()

    def check_graph_min(self):
        """Return None when no games played, used to seed sample graph data."""
        if self.games_played == 0:
            return None

    def set_min(self):
        """Seed minimal sample stats for graph previews (not persisted)."""
        self.games_played = 10
        self.wins = 7
        self.losses = 3

    def graph_view_format_team(self):
        """Build graph-friendly data structure for team and individual stats."""
        sample_team = None
        '''data_test_player = [
          {
            'Stat': 'On Base',
            'Amount': [{"Hit": 177}, {"BB": 111},{"HBP": 6}, {"Error": 3}],
          },
          {
            'Stat': 'Outs',
            'Amount': [{"SO": 175}, {"Sac Fly": 5}, {"GIDP": 14}],
          }
        ]'''
        check = self.check_graph_min()
        if not check:
            sample_team = Team('Sample Team', "Sample Manager", self.message, 10)
            sample_team.set_min()
        ret = [
            {
                'Stat_1': None,
                'Amount_1': []
            },
            {
                'Stat_2': None,
                'Amount_2': []
            }
        ]
        # refactor to match individual player stats
        team = ['games_played', 'wins', 'losses']
        individual = ['BABIP', 'SLG', 'AVG', 'ISO', 'ERA', 'WHIP', 'k_9', 'bb_9']
        attrs = self._get_attrs()
        if sample_team:
            attrs = sample_team._get_attrs()
        # print(attrs)
        for el in attrs:
            # print(el)
            stat = el[0]
            val = el[1]
            # print(stat, val)
            stat_1 = ret[0]['Stat_1']
            stat_2 = ret[1]['Stat_2']
            if stat in team:
                # print(stat)
                if not stat_1:
                    ret[0]['Stat_1'] = 'Team'
                    temp = {stat: val}
                    amt_lst_1 = ret[0]['Amount_1']
                    amt_lst_1.append(temp)
                else:
                    temp = {stat: val}
                    amt_lst_1 = ret[0]['Amount_1']
                    amt_lst_1.append(temp)
            elif stat in individual:
                # print(stat)
                if not stat_2:
                    ret[1]['Stat_2'] = 'Individual'
                    temp = {stat: val}
                    amt_lst_1 = ret[1]['Amount_2']
                    amt_lst_1.append(temp)
                else:
                    temp = {stat: val}
                    # print(temp)
                    amt_lst_2 = ret[1]['Amount_2']
                    amt_lst_2.append(temp)
        return ret

    # string
    def return_dict(self, dict):
        ret = ""
        # print('return dict:', dict)
        for el in dict:
            # print('return dict:', el)
            ret += f"{el}:{dict[el]}\n"
        return ret

    # team lineup
    # list of tuples
    def format_dict(self, dict):
        ret = []
        ret_dict = self.return_dict(dict).split("\n")
        # print(ret_dict)
        for el in ret_dict:
            # not necessary
            indx = el.find(":")
            el = el.replace(":", " ")
            val = el[:indx].strip()
            name = el[indx::].strip()
            ret.append((val, name))
            # temp = None
        ret.pop()
        return ret

    # team stats
    # list of all stats as tuples (exclude lineup)
    def all_stats(self):
        ret_raw = self.__str__().split("\n")
        temp = None
        ret = []
        for el in ret_raw:
            temp = el.split(": ")
            stat = temp[0]
            val = temp[1]
            ret.append((stat, val))
            temp = None
        return ret

    # team stats
    # list of all team stats plus lineup as tuples
    def return_stats(self):
        ret = []
        all = self.all_stats()
        lineup = self.format_dict(self.lineup)
        positions = self.format_dict(self.positions)
        # print('formatted positions:', positions)
        # print('formatted lineup:', lineup)
        ret += all
        ret.append(('Lineup', '----- -----'))
        ret += lineup
        ret.append(('Positions', '----- -----'))
        ret += positions
        ret.pop()
        # print('return stats:', ret)
        return ret

    # ------------------------------------------------------------------------ #
    # getters

    def get_max_roster(self):
        return self.max_roster

    def get_size(self):
        return len(self.players)

    def get_lineup(self):
        ret = ''
        for el in self.lineup:
            ret += f'{el}: {self.lineup[el]}\n'
        return ret

    def get_positions(self):
        ret = ''
        for el in self.positions:
            ret += f'{el}: {self.positions[el]}\n'
        return ret

    def get_games_played(self):
        return self.games_played

    def get_wins(self):
        return self.wins

    def get_losses(self):
        return self.losses

    def get_wl_avg(self):
        return self.wl_avg

    def get_bat_avg(self):
        return self.bat_avg

    def get_player(self, target):
        def _norm(s):
            try:
                return str(s).strip().lower()
            except Exception:
                return s
        target_n = _norm(target)
        for el in self.players:
            if _norm(el.name) == target_n:
                return el
        return None

    def get_manager(self):
        return self.manager

    def get_team_era(self):
        return self.team_era

    def _to_int_safe(self, val):
        """Safely convert value to int, returning 0 on failure."""
        try:
            if val is None:
                return 0
            if isinstance(val, int):
                return val
            if isinstance(val, float):
                return int(val)
            return int(float(str(val).strip()))
        except Exception:
            return 0

    def get_team_hits(self):
        if len(self.players) == 0:
            return 0
        total = 0
        for player in self.players:
            total += self._to_int_safe(player.hit)
        return total

    def get_team_so(self):
        if len(self.players) == 0:
            return 0
        total = 0
        for player in self.players:
            total += self._to_int_safe(player.so)
        return total

    def get_team_runs(self):
        if len(self.players) == 0:
            return 0
        total = 0
        for player in self.players:
            total += self._to_int_safe(player.runs)
        return total

    def get_team_era(self):
        if len(self.players) == 0:
            return 0
        total = 0
        for player in self.players:
            pos = player.positions
            if "pitcher" in pos:
                era_float = float(player.era)
                total += era_float
        return total

    def get_team_k(self):
        if len(self.players) == 0:
            return 0
        total = 0
        for player in self.players:
            pos = player.positions
            if "pitcher" in pos:
                total += self._to_int_safe(player.p_so)
        return total
    # -------------------------------------------------------------------------------------- #
    # setters

    def set_max_roster(self, val):
        if self.max_roster + val < len(self.players):
            new_total = self.max_roster + val
            self.message.show_message(f"Roster max_roster {new_total} cannot be less than current roster {self.max_roster}.", btns_flag=False, timeout_ms=2000)
            # QMessageBox.warning(self, "Input Error", f"Roster max_roster {new_total} cannot be less than current roster {self.max_roster}.")
            return
        self.max_roster = val

    # not in use
    def not_set_lineup(self, order, name):
        if order > self.get_size():
            # print(f'No position {order} in batting order. Try number less than {self.get_size() + 1}\n')
            return
        if order in self.lineup:
            flag_action = input(f'Would you like to replace {self.lineup[order]} at spot {order}? y/n ').lower() == 'y'
            if not flag_action:
                return
            self.lineup[order] = name
        else:
            self.lineup[order] = name

    def set_pos(self, attr, stat, player, parent):
        reply = self.ques_replace(attr, stat, parent)
        if reply == QMessageBox.StandardButton.No:
            return
        self.positions[stat] = player
        # print("positions:\n", self.get_positions())

    def set_wl_avg(self):
        """Recalculate and store win-loss average as formatted string."""
        self.wl_avg = self.calc_wl_avg()

    def set_bat_avg(self):
        """Recalculate and store team batting average across roster."""
        self.bat_avg = self.calc_bat_avg()

    def set_manager(self, val):
        """Set team manager name string."""
        self.manager = val

    def set_lineup(self, attr, stat, player, parent):
        """Set lineup slot 'stat' to player name with replace confirmation."""
        reply = self.ques_replace(attr, stat, parent)
        if reply == QMessageBox.StandardButton.No:
            return
        self.lineup[stat] = player
        # print("positions:\n", self.get_positions())

    def set_games_played(self, val, parent):
        """Increment games_played by val if positive integer; show message otherwise."""
        if self.less_zero(self.games_played, val):
            return
        if isinstance(val, int):
            self.games_played += val
            return
        # QMessageBox.warning(parent, "Input Error", "Enter a value greater than zero.")
        self.message.show_message("Enter a value greater than zero.", btns_flag=False, timeout_ms=2000)

    def set_wins(self, val, parent):
        """Increment wins with guard that wins+losses ≤ games_played."""
        if self.less_zero(self.wins, val):
            return
        if self.games_played > 0:
            if (self.wins + val + self.losses) <= self.games_played:
                self.wins += val
                return
        # QMessageBox.warning(parent, "Input Error", f"Wins-Losses cannot exceed games played\n\n          W:{self.wins} L:{self.losses} G:{self.games_played}.")
        self.message.show_message(f"Wins-Losses cannot exceed games played\n\n          W:{self.wins} L:{self.losses} G:{self.games_played}.", btns_flag=False, timeout_ms=2000)

    def set_losses(self, val, parent):
        """Increment losses with guard that wins+losses ≤ games_played."""
        if self.less_zero(self.losses, val):
            return
        if self.games_played > 0:
            if (self.losses + val) + self.wins <= self.games_played:
                self.losses += val
                return
        # QMessageBox.warning(parent, "Input Error", f"Wins-Losses cannot exceed games played\n\n          W:{self.wins} L:{self.losses} G:{self.games_played}.")
        self.message.show_message(f"Wins-Losses cannot exceed games played\n\n          W:{self.wins} L:{self.losses} G:{self.games_played}.", btns_flag=False, timeout_ms=2000)

    def set_team_era(self):
        """Recalculate and store team ERA from pitchers on roster."""
        self.team_era = self.calc_team_era()

    # -------------------------------------------------------------------------- #
    # calculators

    def calc_wl_avg(self):
        ret = 0
        if self.games_played > 0 and self.wins > 0:
            ret = self.wins / self.games_played
        return self.format_decimal(ret)

    def calc_bat_avg(self):
        num = len(self.players)
        ret = 0
        if num > 0:
            total = 0
            for player in self.players:
                total += float(player.AVG)
            ret = total / num
        return self.format_decimal(ret)

    def calc_team_era(self):
        ret = 0
        count = 0
        for player in self.players:
            if "pitcher" in player.positions:
                count += 1
                ret += float(player.get_era())
        return self.format_decimal(ret)

    # -------------------------------------------------------------------------- #
    # modify team

    def add_player(self, new_player):
        """Append player to roster if capacity allows; ignore otherwise."""
        if len(self.players) < int(self.max_roster):
            self.players.append(new_player)
        else:
            # print('Roster is full')
            return

    def remove_player(self, player):
        """Remove first player matching name from roster and return updated list."""
        indx = None
        for i in range(len(self.players)):
            if self.players[i].name == player:
                # print(self.players)
                # print('index', i)
                # print('player found\n', self.players[i])
                # print('player found\n', self.players[i].name)
                indx = i
        self.players.pop(indx)
        return self.players
