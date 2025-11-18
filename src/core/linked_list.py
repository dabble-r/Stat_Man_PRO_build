from PySide6.QtWidgets import QMessageBox
import random

# --------------------------------------------------

class LinkedList:
    def __init__(self, message=None, name=None, head=None):
        self.admin = {
            "Name": 'League',
            "Commissioner": None,
            "Treasurer": None,
            "Communications": None,
            "Historian": None,
            "Recruitment": None,
            "Start": None,
            "Stop": None
        }
        self.date = None
        self.season = None
        self.location = None
        self.teams = []  # Replaced linked list with built-in list
        self.name = 'League'
        self.message = message
        self.leagueID = self.get_hash()

    # --------------------------------------------------

    def get_count(self):
        """Return the number of teams in the league."""
        return len(self.teams)

    # --------------------------------------------------

    def get_hash(self):
        def indx(a, b):
            index = a.index(b)
            if index == 0:
                return 2
            return index
        ord_lst = [sum(ord(x) * indx(self.admin['Name'], x) for x in self.admin['Name'])]
        return ord_lst.pop()

    def get_rand_hash(self):
        def indx(a, b):
            index = a.index(b)
            if index == 0:
                return 2
            return index
        ord_lst = [sum(ord(x) * indx(self.admin['Name'], x) for x in self.admin['Name'])]
        rand = random.randint(0, 1000)
        return ord_lst.pop() + rand

    def get_incr_hash(self, val):
        return val + 1

    def format_decimal(self, num):
        return "{:.3f}".format(num)

    def __str__(self):
        if not self.teams:
            return ''
        ret = "League\n"
        for team in self.teams:
            ret += f'Team: {team.name}\n'
        return ret

    # --------------------------------------------------

    def get_team_objs_barset(self):
        '''
        example temp: ('team1', 'Beef Sliders', [1,2,3,4,5])
        '''
        if not self.teams:
            return False

        ret = []
        c_ret = []
        t_ret = []
        stat_ret = []

        for indx, team in enumerate(self.teams, start=1):
            count = "team" + str(indx)
            team_name = team.name
            hits = int(team.get_team_hits())
            so = int(team.get_team_so())
            runs = int(team.get_team_runs())
            era = float(team.get_team_era())
            k = int(team.get_team_k())
            avg = round(float(team.get_bat_avg()), 3)
            stats = [hits, so, runs, era, k, avg]

            if hits == 0:
                return False

            c_ret.append(count)
            t_ret.append(team_name)
            stat_ret.append(stats)

        ret.append(t_ret)
        ret.append(stat_ret)
        return ret

    # --------------------------------------------------

    def get_team_objs_barset_spec(self, lst):
        ret = []
        c_ret = []
        t_ret = []
        stat_ret = []
        check_team = lst

        for indx, team in enumerate(self.teams, start=1):
            if team.name in check_team:
                count = "team" + str(indx)
                team_name = team.name
                hits = int(team.get_team_hits())
                so = int(team.get_team_so())
                runs = int(team.get_team_runs())
                era = float(team.get_team_era())
                k = int(team.get_team_k())
                avg = round(float(team.get_bat_avg()), 3)
                stats = [hits, so, runs, era, k, avg]

                if hits == 0:
                    return False

                c_ret.append(count)
                t_ret.append(team_name)
                stat_ret.append(stats)

        ret.append(t_ret)
        ret.append(stat_ret)
        return ret

    # --------------------------------------------------

    # deprecated
    def get_team_objs_lineseries(self):
        '''example temp:
          ('team1', 'Beef Sliders', 0.432)
        '''
        if not self.teams:
            return None
        ret = [[], [], []]
        for indx, team in enumerate(self.teams, start=1):
            count = "team" + str(indx)
            team_name = team.name
            avg = team.get_bat_avg()
            ret[0].append(count)
            ret[1].append(team_name)
            ret[2].append(avg)
        return ret

    # --------------------------------------------------

    def get_admin(self):
        ret = 'League Admin\n'
        ret += f" League Name: {self.admin['League Name']}\n"
        ret += f" Commissioner: {self.admin['Commissioner']}\n"
        ret += f" Historian: {self.admin['Historian']}\n"
        ret += f" Treasurer: {self.admin['Treasurer']}\n"
        ret += f" Recruitment: {self.admin['Recruitment']}\n"
        ret += f" Communications: {self.admin['Communications']}\n"
        ret += f" Season Start: {self.admin['Season Start']}\n"
        ret += f" Season End: {self.admin['Season End']}"
        return ret

    def return_dict(self, dict):
        ret = ""
        for el in dict:
            ret += f"{el}:{dict[el]}\n"
        return ret

    # team lineup
    # list of tuples
    def format_dict(self, dict):
        ret = []
        ret_dict = self.return_dict(dict).split("\n")
        for el in ret_dict:
            indx = el.find(":")
            el = el.replace(":", " ")
            val = el[:indx].strip()
            name = el[indx::].strip()
            ret.append((val, name))
        ret.pop()
        return ret

    # team stats
    # list of all team stats plus lineup as tuples
    def return_admin(self):
        admin = self.format_dict(self.admin)
        return admin

    def ques_replace(self, attr, stat, parent):
        existing_val = getattr(self, attr)[stat]
        if existing_val:
            reply = QMessageBox.question(parent, "Input Error", f"Would you like to replace {existing_val} at {stat}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            return reply
        return None

    # --------------------------------------------------

    def add_team(self, val):
        """Append a Team to the end of the league list."""
        self.teams.append(val)

    # --------------------------------------------------

    def remove_team(self, target):
        """Remove first Team whose name matches target."""
        for i, team in enumerate(self.teams):
            if team.name == target:
                self.teams.pop(i)
                return

    # --------------------------------------------------

    def find_team(self, target):
        """Return Team by case-insensitive name match, or None if not present."""
        def _norm(s):
            try:
                return str(s).strip().lower()
            except Exception:
                return s
        target_n = _norm(target)
        for team in self.teams:
            if _norm(team.name) == target_n:
                return team
        return None

    # --------------------------------------------------

    def find_teamID(self, target):
        """Return Team by exact teamID match (int), or None if not present."""
        for team in self.teams:
            if team.teamID == target:
                return team
        return None

    # --------------------------------------------------

    def find_player(self, target):
        """Find player by name across all teams."""
        target_lower = target.lower()
        for team in self.teams:
            for player in team.players:
                if player.name.lower() == target_lower:
                    return player
        return None

    # --------------------------------------------------

    def find_player_by_number(self, target: int) -> list:
        """Find all players with matching number across all teams."""
        ret = []
        for team in self.teams:
            for player in team.players:
                if int(player.number) == target:
                    ret.append(player)
        return ret

    # --------------------------------------------------

    def view_all(self):
        """Return string summary of teams and first-position players across league."""
        if not self.teams:
            return ''
        ret = ''
        for team in self.teams:
            ret += f'\nTeam: {team.name}\nPlayers: {[{x.name: x.positions[0]} for x in team.players]}\n'
        return ret

    # --------------------------------------------------

    def set_admin(self, attr, stat, val, parent):
        if 'Season' in stat:
            self.admin[stat] = val
            return

        reply = self.ques_replace(attr, stat, parent)
        if reply == QMessageBox.StandardButton.No:
            return

        self.admin[stat] = val

    # --------------------------------------------------

    def isDefaultName(self):
        return self.admin['Name'] == 'League'

    # --------------------------------------------------

    def get_all_players_num(self):
        """Return list of (name, team, number) tuples for all players."""
        ret = []
        for team in self.teams:
            for player in team.players:
                team_val = player.team.name if hasattr(player.team, 'name') else player.team
                ret.append((player.name, team_val, str(player.number)))
        return ret

    # --------------------------------------------------

    def get_all_players_avg(self):
        """Return list of (name, team, avg) tuples for all players."""
        ret = []
        for team in self.teams:
            for player in team.players:
                ret.append((player.name, player.team, player.AVG))
        return ret

    # --------------------------------------------------

    def get_all_avg(self):
        """Return list of (name, roster, avg) tuples for all teams."""
        ret = []
        for team in self.teams:
            name = team.name
            roster = team.max_roster
            avg = self.format_decimal(float(team.get_bat_avg()))
            ret.append((name, roster, avg))
        return ret

    # --------------------------------------------------

    def get_all_wl(self):
        """Return list of (name, roster, wl_avg) tuples for all teams."""
        ret = []
        for team in self.teams:
            name = team.name
            roster = team.max_roster
            avg = self.format_decimal(float(team.get_wl_avg()))
            ret.append((name, roster, avg))
        return ret

    # --------------------------------------------------

    def get_all_team_names(self):
        """Return list of all team names."""
        if not self.teams:
            return None
        return [team.name for team in self.teams]

    # --------------------------------------------------

    def get_team_era(self):
        '''
        team = all players
        players = [a,b,c,d,e,f,g]
        a.positions = [a,b,c,d,pitcher,e,f,g]
        if 'pitcher' in a.positions:
          temp = a.era
          total += temp
          temp = 0
        '''
        ret = []
        if not self.teams:
            return self.format_decimal(ret)
        for team in self.teams:
            total = 0
            for player in team.players:
                if 'pitcher' in player.positions:
                    total += float(player.era)
            ret.append((team.name, str(total)))
        return ret

    # --------------------------------------------------

    def get_all_objs(self):
        """Return list of all Team objects."""
        return self.teams.copy()

    # --------------------------------------------------
