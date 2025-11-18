import csv
import os 
import sqlite3 
import json
from pathlib import Path
from src.core.league import League 
from src.core.team import Team 
from src.core.player import Player, Pitcher
from typing import Dict, Any, Optional


# get csv name 
# get csv file path 
# check if csv file exists at file path


# get db name 
# get db file path 
# check if db exists 
  # if db exists, user dialog prompt 
    # overwrite teams, players, pitchers ?
    # update data ?

# get ALL table names 
# iterate over each table 
# overwrite / update team/player/pitcher as user request


class Load():
  def __init__(self, league, message, file_dir, db_path=None, csv_path=None, parent=None):
    
    self.file_dir = file_dir
    self.league = league
    self.message = message
    self.parent = parent
    self.db_path = db_path
    self.csv_path = csv_path

    # init league, team, player/pitcher instances
    self.league = None 
    self.teams = [] 
    self.players = []
    
  def db_exists(self):
    db_path = Path(self.db_path)
    db_uri = f"file:{db_path}?mode=rw"
    try:
        con = sqlite3.connect(db_uri, uri=True, timeout=60)
        cur = con.cursor()
        return con, cur
    except sqlite3.OperationalError:
        print(f"Database '{db_path}' does not exist!")
        return None

  def open_db(self):
    # Connect and insert
    
    if self.db_exists() is not None:
      con, cur = self.db_exists()
      return con, cur
    
    con = sqlite3.connect(self.db)
    cur = con.cursor()
    return con, cur
  
  def get_con(self):
    try: 
      if self.db:
        con = sqlite3.connect(self.db) 
        return con

    except:
      #print("Error connecting to db!")
      return None 
  
  def get_cur(self):
    try: 
      if self.con:
        cur = self.con.cursor()
        return cur 
    except:
      #print('Error getting cursor!')
      return None
    
  def table_exists(self, con, cur, table_name):
    #con, cur = self.open_db()
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?;
    """, (table_name,))

    return cur.fetchone() is not None

  def field_exists(self, table, field):
    con, cur = self.open_db()
    cur.execute(f"PRAGMA table_info({table});")
    columns = [row[1] for row in cur.fetchall()]  # row[1] is the column name
    return field in columns 
  
  def scan_ret(self, lst, target):
    for i in range(len(lst)):
      temp = lst[i][0]
      ##print(temp[0] == target)
      if target == temp:
        return True
    return False

  def init_new_db(self):
    # Enable foreign key constraints
    con, cur = self.open_db()
    cur.execute("PRAGMA foreign_keys = ON")
    
    con.commit()
    con.close()
    
    self.init_league()
    self.init_team()
    self.init_player()
    self.init_pitcher()

  def init_league(self):
      con, cur = self.open_db()
      
      # Create league table
      cur.execute(f"""
          CREATE TABLE IF NOT EXISTS league (
              leagueID INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              commissioner TEXT,
              treasurer TEXT,
              communications TEXT,
              historian TEXT,
              recruitment TEXT,
              start TEXT,
              stop TEXT
          )
      """)

      cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_league_unique
        ON league(leagueID);
    """)

      # set up league cols and fields
      cur.execute("""
      INSERT INTO league (
          leagueID, name, commissioner, treasurer,
          communications, historian, recruitment,
          start, stop
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      """, (
          self.league.leagueID,
          self.league.name,
          self.league.admin['Commissioner'],
          self.league.admin['Historian'],
          self.league.admin['Recruitment'],
          self.league.admin['Communications'],
          self.league.admin['Historian'],
          self.league.admin['Season Start'],
          self.league.admin['Season End']
      ))

      # commit created tables and close
      con.commit()
      con.close()
    # call init league
    
  def init_team(self):
      con, cur = self.open_db()

      # Create team table
      cur.execute("""
        CREATE TABLE IF NOT EXISTS team (
            teamID INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            leagueID INTEGER NOT NULL,
            league TEXT,
            logo TEXT,
            manager TEXT,
            players TEXT,         -- JSON stringified list
            lineup TEXT,          -- JSON stringified dict
            positions TEXT,       -- JSON stringified dict
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            wl_avg REAL DEFAULT 0.0,
            bat_avg REAL DEFAULT 0.0,
            team_era REAL DEFAULT 0.0,
            max_roster INTEGER,
            FOREIGN KEY (leagueID) REFERENCES league(leagueID)
        )
      """) 

      cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_team_unique
        ON team(teamID);
      """)

      con.commit()
      con.close()
    # call init team
    
  def init_player(self):
      con, cur = self.open_db()
      
      # Create player table
      cur.execute("""
          CREATE TABLE IF NOT EXISTS player (
              playerID INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              leagueID INTEGER NOT NULL,
              teamID INTEGER NOT NULL,
              number INTEGER,
              team TEXT,
              positions TEXT,       -- JSON stringified list
              pa INTEGER DEFAULT 0,
              at_bat INTEGER DEFAULT 0,
              fielder_choice INTEGER DEFAULT 0,
              hit INTEGER DEFAULT 0,
              bb INTEGER DEFAULT 0,
              hbp INTEGER DEFAULT 0,
              put_out INTEGER DEFAULT 0,
              so INTEGER DEFAULT 0,
              hr INTEGER DEFAULT 0,
              rbi INTEGER DEFAULT 0,
              runs INTEGER DEFAULT 0,
              singles INTEGER DEFAULT 0,
              doubles INTEGER DEFAULT 0,
              triples INTEGER DEFAULT 0,
              sac_fly INTEGER DEFAULT 0,
              OBP REAL DEFAULT 0.0,
              BABIP REAL DEFAULT 0.0,
              SLG REAL DEFAULT 0.0,
              AVG REAL DEFAULT 0.0,
              ISO REAL DEFAULT 0.0,
              image TEXT,
              FOREIGN KEY (leagueID) REFERENCES league(leagueID),
              FOREIGN KEY (teamID) REFERENCES team(teamID)
          )
      """)

      cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_player_unique
        ON player(playerID);
      """)
      
      con.commit()
      con.close()
    
  def init_pitcher(self):
      # Create pitcher table
      con, cur = self.open_db()
      cur.execute("""
      
     
        CREATE TABLE IF NOT EXISTS pitcher (
            playerID INTEGER PRIMARY KEY,
            leagueID INTEGER NOT NULL,
            teamID INTEGER NOT NULL,
            name TEXT NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            era REAL DEFAULT 0.0,
            games_played INTEGER DEFAULT 0,
            games_started INTEGER DEFAULT 0,
            games_completed INTEGER DEFAULT 0,
            shutouts INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            save_ops INTEGER DEFAULT 0,
            ip REAL DEFAULT 0.0,
            p_at_bats INTEGER DEFAULT 0,
            p_hits INTEGER DEFAULT 0,
            p_runs INTEGER DEFAULT 0,
            er INTEGER DEFAULT 0,
            p_hr INTEGER DEFAULT 0,
            p_hb INTEGER DEFAULT 0,
            p_bb INTEGER DEFAULT 0,
            p_so INTEGER DEFAULT 0,
            WHIP REAL DEFAULT 0.0,
            p_AVG REAL DEFAULT 0.0,
            k_9 REAL DEFAULT 0.0,
            bb_9 REAL DEFAULT 0.0,
            FOREIGN KEY (playerID) REFERENCES player(playerID),
            FOREIGN KEY (leagueID) REFERENCES league(leagueID),
            FOREIGN KEY (teamID) REFERENCES team(teamID)
        )
    """)
      
      cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pitcher_unique
        ON pitcher(playerID);
      """)
      
      con.commit()
      con.close()
    
  def save_team(self):
    def keep_attrs(obj):
      keep = ['teamID', 'name', 'leagueID', 'league', 'logo', 'manager', 'players', 'lineup', 'positions', 'wins', 'losses', 'games_played', 'wl_avg', 'bat_avg', 'team_era', 'max_roster']
      dir_list = [x for x in keep if self.sql_safe(x)] 
      ##print(dir_list)
      return dir_list
    
    con, cur = self.open_db()

    if self.table_exists(con, cur, 'team'):
        #print('league exists--table team exists')
        
        objsTeam = self.league.get_all_objs()

        res = cur.execute(f"SELECT teamID FROM team")
        ret = res.fetchall()
        
        # check for league name duplicate 
        if len(ret) == 0:
          #print('no teams in db!')
          for i in range(len(objsTeam)):
            ##print('team to save:', objsTeam[i].name)
            team_name = objsTeam[i].name
            team = objsTeam[i]

            '''if self.scan_ret(ret, team.teamID):
              #print('teamID already exists!')
              continue'''
            
            dir_list = keep_attrs(team) 
            print(dir_list)
            cols = []
            vals = []
            check_type = [int, str, float, dict, list, type(None)]
            ##print(exclude_attrs(team))

            for el in dir_list:
              val = getattr(team, el)
              print('el--val:', el, val)
              

              if isinstance(val, (dict)):
                val = json.dumps(val)

              elif isinstance(val, (list)):
                roster = []
                for el in val:
                  ##print(el)
                  player_name = el.name
                  roster.append(player_name)
                
                roster_json = json.dumps(roster)
                ##print(roster_json, type(roster_json))
                val = roster_json
                el = 'players'
              
              elif type(val) not in check_type:
                league_name = val.name 
                val = league_name
              
              cols.append(el)
              vals.append(val)

            placeholders = ", ".join(["?"] * len(vals))
            column_str = ", ".join(cols)

            ##print(placeholders)
            ##print(column_str)
            ##print(vals)
            
            cur.execute(
                  f"INSERT INTO team ({column_str}) VALUES ({placeholders})",
                  tuple(vals)
              )
            
          con.commit()

        # check for league name duplicate 
        elif len(ret) >= 1:
          #print('teams in db!')
          res = cur.execute(f"SELECT teamID FROM team")
          ret = res.fetchall()

          for i in range(len(objsTeam)):
            ##print('team to save:', objsTeam[i].name)
            team = objsTeam[i]
            team_ID = team.teamID
            team_name = team.name

            if self.scan_ret(ret, team_ID):
              #print('teamID already exists!')
              self.update_team(con, cur, team, keep_attrs)
            
            else:
              dir_list = keep_attrs(team)
              ##print(dir_list)
              cols = []
              vals = []
              ##print(exclude_attrs(team))

              for el in dir_list:
                val = getattr(team, el)
                ##print('val:', val, type(val))
                check_type = [int, str, float, dict, list, type(None)]

                if isinstance(val, (dict)):
                  val = json.dumps(val)

                elif isinstance(val, (list)):
                  roster = []
                  for el in val:
                    ##print(el)
                    player_name = el.name
                    roster.append(player_name)
                  
                  roster_json = json.dumps(roster)
                  ##print(roster_json, type(roster_json))
                  val = roster_json
                  el = 'players'
                
                elif type(val) not in check_type:
                  league_name = val.name 
                  val = league_name
                
                cols.append(el)
                vals.append(val)

              placeholders = ", ".join(["?"] * len(vals))
              column_str = ", ".join(cols)

              ##print(placeholders)
              ##print(column_str)
              ##print(vals)
              
              cur.execute(
                    f"INSERT INTO team ({column_str}) VALUES ({placeholders})",
                    tuple(vals)
                )
              
            con.commit()

        con.close()
  
  def update_team(self, con, cur, team_obj, keep_func):
    #print('Update: ', team_obj.name)
    dir_list = keep_func(team_obj)
    team_name = team_obj.name 
    team_ID = team_obj.teamID 
    ##print(team_obj.games_played)

    ##print(dir_list)
    cols = []
    vals = []
    ##print(exclude_attrs(team))

    for el in dir_list:
      val = getattr(team_obj, el)
      ##print('val:', el, val, type(val))
      check_type = [int, str, float, dict, list, type(None)]

      if isinstance(val, (dict)):
        val = json.dumps(val)

      elif isinstance(val, (list)):
        roster = []
        for el in val:
          ##print(el)
          player_name = el.name
          roster.append(player_name)
        
        roster_json = json.dumps(roster)
        ##print(roster_json, type(roster_json))
        val = roster_json
        el = 'players'
      
      elif type(val) not in check_type:
        league_name = val.name 
        val = league_name
      
      cols.append(el)
      vals.append(val)

    #placeholders = ", ".join(["?"] * len(vals))
    #column_str = ", ".join(cols)

    set_clause = ", ".join([f"{col} = ?" for col in cols])
    sql = f"UPDATE team SET {set_clause} WHERE teamID = ?"

    ##print(cols)
    ##print(vals)
    ##print(sql)
    
    # modify command
    cur.execute(sql, vals + [team_ID])
    con.commit()
     
  def save_player(self):
    ##print('save player!')
    def keep_attrs_player(obj):
      keep = ['playerID', 'name', 'leagueID', 'teamID', 'number', 'team', 'positions', 'pa', 'at_bat', 'fielder_choice', 'hit', 'bb', 'hbp', 'put_out', 'so', 'hr', 'rbi', 'runs', 'singles', 'doubles', 'triples', 'sac_fly', 'OBP', 'BABIP', 'SLG', 'AVG', 'ISO', 'image']
      dir_list = [x for x in keep if self.sql_safe(x)] 
      return dir_list
    
    def keep_attrs_pitcher(obj):
      keep = ['name', 'playerID', 'teamID', 'leagueID', 'wins', 'losses', 'era', 'games_played', 'games_completed', 'shutouts', 'save_ops', 'ip', 'p_at_bats', 'p_hits', 'p_runs', 'er', 'p_hb', 'p_so', 'WHIP', 'p_avg', 'k_9', 'bb_9']
      dir_raw = dir(obj)
      dir_list = [x for x in keep if self.sql_safe(x)]
      return dir_list
    
    con, cur = self.open_db()

    if not self.table_exists(con, cur, 'team'):
      #print('team table does not exist!')
      return

    elif not self.table_exists(con, cur, 'player'):
      #print('player table does not exist!')
      return
      
    res = cur.execute("SELECT teamID FROM team")
    ret = [row[0] for row in res.fetchall()]

    # teams exist in the DB/league
    if len(ret) >= 1:
      objsTeam = self.league.get_all_objs()
      ##print(objsTeam)

      for i in range(len(objsTeam)):
        ##print('player team to save:', objsTeam[i])
        team = objsTeam[i]
        team_name = team.name 
        team_ID = team.teamID
        players = team.players

        res = cur.execute("SELECT playerID FROM player")
        ret = [row[0] for row in res.fetchall()]
          
        for player in players: 
          player_name = player.name 
          player_ID = player.playerID
          player_team_ID = player.teamID 
          isPitcher = 'pitcher' in player.positions 
          
          # does player exist in DB ???
          if player_ID in ret:
            #print('match player, wish to update?')

            # is the player a pitcher?
            # if yes, update pitcher and update player tables
            if isPitcher:
              #print('match pitcher, wish to update?')
              self.update_pitcher(con, cur, player, keep_attrs_pitcher)
              self.update_player(con, cur, player, keep_attrs_player) 
              continue

            # if not, update player table only
            self.update_player(con, cur, player, keep_attrs_player)
            continue

          # if playerID not in DB, create new player
          elif player_ID not in ret:
            #print('no match player, wish to create?')

            cols = []
            vals = []

            # if player is a pitcher 
            # exclude players attrs, except name, playerID, teamID, leagueID
            if isPitcher:
              #print('is a pitcher')
              res = cur.execute("SELECT playerID FROM pitcher")
              ret = [row[0] for row in res.fetchall()]

              dir_list = keep_attrs_pitcher(player)
              ##print(dir_list)
          
              for el in dir_list:
                val = getattr(player, el)
                ##print(val, type(val))

                if isinstance(val, (dict, list)):
                  ##print('player val:', el, val, type(val))
                  # represents player positions
                  val = json.dumps(val)

                cols.append(el)
                vals.append(val) 

              placeholders = ", ".join(["?"] * len(vals))
              column_str = ", ".join(cols)

              ##print(placeholders)
              ##print(column_str)
              ##print(cols)
              ##print(vals)
              
              cur.execute(
                    f"INSERT INTO pitcher ({column_str}) VALUES ({placeholders})",
                    tuple(vals)
                )
            
              con.commit()
          
          # reset cols and vals in case of Pitcher isntance
          cols = []
          vals = []

          # regardless of pitcher instance, update all Player attributes
          dir_list = keep_attrs_player(player)
          #print(dir_list)

          for el in dir_list:
            val = getattr(player, el)
            ##print(val, type(val))

            if isinstance(val, (dict, list)):
              ##print('player val:', el, val, type(val))
              # represents player positions
              val = json.dumps(val)
            
            elif el == 'team':

              val = getattr(player, el)
              val = val.name

            cols.append(el)
            vals.append(val) 

          placeholders = ", ".join(["?"] * len(vals))
          column_str = ", ".join(cols)

          #print(placeholders)
          #print(column_str)
          #print(cols)
          #print(vals) 
        
          cur.execute(
                f"INSERT INTO player ({column_str}) VALUES ({placeholders})",
                tuple(vals)
            )
        
          con.commit()

        self.update_team_roster(con, cur, players, team_ID)

    con.close()

  def update_player(self, con, cur, player_obj, keep_func):
    #print('update player:', player_obj.name)
    dir_list = keep_func(player_obj)
    team_name = player_obj.name 
    team_ID = player_obj.teamID
    player_ID = player_obj.playerID
    #print(player_obj.at_bat)

    ##print(dir_list)
    cols = []
    vals = []
    ##print(exclude_attrs(team))

    for el in dir_list:
      val = getattr(player_obj, el)
      ##print('val:', el, val, type(val))
      check_type = [int, str, float, dict, list, type(None)]

      if isinstance(val, (dict)):
        val = json.dumps(val)

      elif isinstance(val, (list)):
        pos = []
        for el in val:
          ##print(el)
          pos.append(el)
        
        pos_json = json.dumps(pos)
        ##print(roster_json, type(roster_json))
        val = pos_json
        el = 'positions'
      
      elif type(val) not in check_type:
        league_name = val.name 
        val = league_name
      
      cols.append(el)
      vals.append(val)

    #placeholders = ", ".join(["?"] * len(vals))
    #column_str = ", ".join(cols)

    set_clause = ", ".join([f"{col} = ?" for col in cols])
    sql = f"UPDATE player SET {set_clause} WHERE playerID = ?"

    #print(cols)
    #print(vals)
    #print(sql)
    
    # modify command
    cur.execute(sql, vals + [player_ID])
    con.commit()

  def update_pitcher(self, con, cur, player_obj, keep_func):
    #print('update player/pitcher:', player_obj.name)
    dir_list = keep_func(player_obj)
    team_name = player_obj.name 
    team_ID = player_obj.teamID
    player_ID = player_obj.playerID
    ##print(team_obj.games_played)

    ##print(dir_list)
    cols = []
    vals = []
    ##print(exclude_attrs(team))

    for el in dir_list:
      val = getattr(player_obj, el)
      ##print('val:', el, val, type(val))
      check_type = [int, str, float, dict, list, type(None)]

      if isinstance(val, (dict)):
        val = json.dumps(val)

      elif isinstance(val, (list)):
        pos = []
        for el in val:
          ##print(el)
          player_name = el.name
          pos.append(player_name)
        
        pos_json = json.dumps(pos)
        ##print(roster_json, type(roster_json))
        val = pos_json
        el = 'positions'
      
      elif type(val) not in check_type:
        league_name = val.name 
        val = league_name
      
      cols.append(el)
      vals.append(val)

    #placeholders = ", ".join(["?"] * len(vals))
    #column_str = ", ".join(cols)

    set_clause = ", ".join([f"{col} = ?" for col in cols])
    sql = f"UPDATE pitcher SET {set_clause} WHERE playerID = ?"

    print(cols)
    print(vals)
    print(sql)
    
    # modify command
    cur.execute(sql, vals + [player_ID])
    con.commit()
     
  def update_team_roster(self, con, cur, roster, teamID):
    res = cur.execute("SELECT teamID FROM team")
    ret = res.fetchall()
    roster_JSON = json.dumps([x.name for x in roster])
    team_ids = [row[0] for row in ret]

    ##print(ret)
    if len(ret) == 0:
      #print('No teams in league!')
      return
    
    if teamID in team_ids:
      #print('match: ', teamID)
      
      cur.execute(
          """UPDATE team 
          SET players = ? 
          WHERE teamID = ?
          """, 
          (roster_JSON, teamID)
        )
      
      con.commit()
      
  def sql_safe(self, val):
    return isinstance(val, (type(None), int, float, str))

                    # -------------------------------------------------------------------------------- #

def load_all_from_db(db_path: str, parent) -> Optional[League]:
  """
  Build a full League league from an existing SQLite DB and update the GUI.
  - Reads league, teams, players, pitchers
  - Reconstructs Team and Player/Pitcher objects and relationships
  - Assigns the league to parent and refreshes views
  """
  def _row_factory(cursor, row):
    return {description[0]: row[idx] for idx, description in enumerate(cursor.description)}

  def _parse_json(value, default):
    if value is None or value == "":
      return default
    try:
      return json.loads(value)
    except Exception:
      return default

  if not db_path or not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    return None

  con = sqlite3.connect(db_path)
  con.row_factory = _row_factory
  cur = con.cursor()

  league = League()

  # Load league (first row)
  try:
    cur.execute("SELECT * FROM league LIMIT 1")
    row_league = cur.fetchone()
    if row_league:
      # Map DB -> League admin
      league.admin['Name'] = row_league.get('name')
      league.admin['Commissioner'] = row_league.get('commissioner')
      league.admin['Treasurer'] = row_league.get('treasurer')
      league.admin['Communications'] = row_league.get('communications')
      league.admin['Historian'] = row_league.get('historian')
      league.admin['Recruitment'] = row_league.get('recruitment')
      # League uses 'Start'/'Stop'
      league.admin['Start'] = row_league.get('start')
      league.admin['Stop'] = row_league.get('stop')
      # Align IDs if present
      if 'leagueID' in row_league and row_league['leagueID'] is not None:
        try:
          league.leagueID = int(row_league['leagueID'])
        except Exception:
          pass
  except Exception as e:
    print(f"Error loading league: {e}")

  # Preload pitchers into dict by playerID
  pitchers_by_player_id: Dict[int, Dict[str, Any]] = {}
  try:
    cur.execute("SELECT * FROM pitcher")
    for prow in cur.fetchall() or []:
      pid = prow.get('playerID')
      if pid is not None:
        pitchers_by_player_id[int(pid)] = prow
  except Exception as e:
    # Pitcher table may not exist yet; continue
    print(f"Pitcher load note: {e}")

  # Load teams first and index by teamID
  teams_by_id: Dict[int, Team] = {}
  try:
    cur.execute("SELECT * FROM team")
    for trow in cur.fetchall() or []:
      name = trow.get('name') or 'Team'
      manager = trow.get('manager') or 'Manager'
      team = Team(league, name, manager)

      # IDs
      if trow.get('teamID') is not None:
        try:
          team.teamID = int(trow['teamID'])
        except Exception:
          pass
      if trow.get('leagueID') is not None:
        try:
          team.leagueID = int(trow['leagueID'])
        except Exception:
          pass

      # Simple fields
      # Keep logo as string path - GUI will convert to QIcon when displaying
      team.logo = trow.get('logo')
      team.wins = int(trow.get('wins') or 0)
      team.losses = int(trow.get('losses') or 0)
      team.games_played = int(trow.get('games_played') or 0)
      team.wl_avg = float(trow.get('wl_avg') or 0.0)
      team.bat_avg = float(trow.get('bat_avg') or 0.0)
      team.team_era = float(trow.get('team_era') or 0.0)
      if trow.get('max_roster') is not None:
        try:
          team.max_roster = int(trow['max_roster'])
        except Exception:
          pass

      # JSON fields
      team.lineup = _parse_json(trow.get('lineup'), team.lineup)
      team.positions = _parse_json(trow.get('positions'), team.positions)

      league.add_team(team)
      teams_by_id[team.teamID] = team
  except Exception as e:
    print(f"Error loading teams: {e}")

  # Load players and attach to teams
  try:
    cur.execute("SELECT * FROM player")
    for prow in cur.fetchall() or []:
      team_id = prow.get('teamID')
      if team_id is None:
        continue
      try:
        team_id_int = int(team_id)
      except Exception:
        continue
      team = teams_by_id.get(team_id_int)
      if not team:
        continue

      positions_list = _parse_json(prow.get('positions'), [])
      pid = prow.get('playerID')
      is_pitcher_row = False
      pitcher_row = None
      if pid is not None:
        try:
          pid_int = int(pid)
          pitcher_row = pitchers_by_player_id.get(pid_int)
          is_pitcher_row = pitcher_row is not None or ('pitcher' in positions_list)
        except Exception:
          pass

      if is_pitcher_row:
        player = Pitcher(prow.get('name') or 'Player', int(prow.get('number') or 0), team, league, positions_list)
      else:
        player = Player(prow.get('name') or 'Player', int(prow.get('number') or 0), team, league, positions_list)

      # IDs
      if pid is not None:
        try:
          player.playerID = int(pid)
        except Exception:
          pass
      player.teamID = team.teamID
      player.leagueID = league.leagueID

      # Offensive stats
      for key in ['pa','at_bat','fielder_choice','hit','bb','hbp','put_out','so','hr','rbi','runs','singles','doubles','triples','sac_fly']:
        try:
          setattr(player, key, int(prow.get(key) or 0))
        except Exception:
          setattr(player, key, 0)
      for key in ['OBP','BABIP','SLG','AVG','ISO']:
        try:
          setattr(player, key, float(prow.get(key) or 0.0))
        except Exception:
          setattr(player, key, 0.0)
      # Keep image as string path for player - stat dialog handles conversion
      image_path = prow.get('image')
      if image_path and image_path not in (0, '0', 0.0, '0.0', ''):
          player.image = image_path
      else:
          player.image = None

      # Pitching stats if applicable
      if pitcher_row is not None and isinstance(player, Pitcher):
        numeric_pitch = ['wins','losses','era','games_played','games_started','games_completed','shutouts','saves','save_ops','ip','p_at_bats','p_hits','p_runs','er','p_hr','p_hb','p_bb','p_so','WHIP','p_avg','k_9','bb_9']
        for key in numeric_pitch:
          val = pitcher_row.get(key)
          try:
            if key in ['era','WHIP','p_avg','k_9','bb_9','ip']:
              setattr(player, key, float(val or 0.0))
            else:
              setattr(player, key, int(val or 0))
          except Exception:
            setattr(player, key, 0 if key not in ['era','WHIP','p_avg','k_9','bb_9','ip'] else 0.0)

      team.add_player(player)
  except Exception as e:
    print(f"Error loading players: {e}")

  con.close()

  # Attach to GUI and refresh
  setattr(parent, 'league', league)
  try:
    if hasattr(parent, 'refresh_view') and callable(parent.refresh_view):
      parent.refresh_view()
  except Exception as e:
    print(f"Refresh note: {e}")

  return league

  # deprecated
  # import csv table/field per table
  # this will not work 
  # program should use pre exisitng new db init if no db exists 
    # cols definitions and data types will clash / unnecessary
  def import_csv_to_sqlite(self, db_path, path):
    print('db path - import csv', db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    tables = []
    with open(path, "r") as f:   
        # Create a csv reader object
        reader = csv.reader(f)
        header = next(reader)

        # Insert each row into the table
        for row in reader:
          tables.append(row)

    con.close()

                           # -------------------------------------------------------------------------------- #

  def load_master(self):
    #self.db_path = db_path
    #self.csv_path = csv_path

    #self.upsert_team_from_csv(self.csv_path)
    #self.upsert_player_from_csv(self.csv_path)

    self.upsert_test(self.csv_path)

                        # ------------------------------------------------------------------------------------ #
  # test func 
  # experimental - upsert team
  def upsert_test(self, csv_path):
    con, cur = self.open_db()
    print('upsert team')

    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        #print(reader)
        
        for row in reader: 
          print(row)
          #print('team row keys:', row.keys())
          #print('team row vals:', row.values())
          #print('team row items:', row.items())

          if row.get("source_table") == "league":
              print('source - league:', row)
          
          if row.get("source_table") == "team":
              print('source - team:', row)

          if row.get("source_table") == "player":
              print('source - player:', row)
          
          if row.get("source_table") == "pitcher":
              print('source - pitcher:', row)
              
              

  # experimental - upsert team
  def upsert_team_from_csv(self, csv_path):
    con, cur = self.open_db()
    print('upsert team')

    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        #print(reader)
        
        for row in reader:
            #print('team row keys:', row.keys())
            #print('team row vals:', row.values())
            #print('team row items:', row.items())
            
            if row.get("source_table") != "team":
                print('team row-not team:', row)
                continue

            teamID = row.get("teamID")
            team_name = row.get("name")

            # Parse JSON fields
            for field in ["players", "lineup", "positions"]:
                raw = row.get(field, "")
                try:
                    parsed = json.loads(raw) if raw else []
                    row[field] = json.dumps(parsed)
                except json.JSONDecodeError:
                    row[field] = json.dumps([])

            # Check if team exists
            cur.execute("SELECT teamID FROM team WHERE teamID = ?", (teamID,))
            exists = cur.fetchone()

            if exists:
                response = self.message.show_message(f"Would you like to overwrite {team_name} stats?")
                if response.lower() != "yes":
                    continue

                update_fields = [f"{k}=?" for k in row if k != "teamID" and k != "source_table"]
                print('team update fields:', update_fields)
                update_sql = f"UPDATE team SET {', '.join(update_fields)} WHERE teamID = ?"
                values = [row[k] for k in row if k != "teamID" and k != "source_table"] + [teamID]
                cur.execute(update_sql, values)
            else:
                insert_fields = [k for k in row if k != "source_table"]
                insert_sql = f"INSERT INTO team ({', '.join(insert_fields)}) VALUES ({', '.join(['?' for _ in insert_fields])})"
                values = [row[k] for k in insert_fields]
                cur.execute(insert_sql, values)

    con.commit()
    cur.close()
    con.close()

  # experimental - player/pitcher load
  def upsert_player_from_csv(self, csv_path):
    con, cur = self.open_db()
    print('upsert player')

    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        #print(reader)
        

        for row in reader:
            #print('player row:', row)
            if row.get("playerId") != "player":
                continue

            playerID = row.get("playerID")
            player_name = row.get("name")

            # Parse positions
            raw_positions = row.get("positions", "")
            try:
                positions_list = json.loads(raw_positions)
                row["positions"] = json.dumps(positions_list)
            except json.JSONDecodeError:
                positions_list = []
                row["positions"] = json.dumps([])

            # Check if player exists
            cur.execute("SELECT playerID FROM player WHERE playerID = ?", (playerID,))
            exists = cur.fetchone()

            if exists:
                response = self.message.show_message(f"Would you like to overwrite {player_name}?")
                if response.lower() == "yes":
                    update_fields = [f"{k}=?" for k in row if k != "playerID" and k != "source_table"]
                    print('player update fields:', update_fields)
                    update_sql = f"UPDATE player SET {', '.join(update_fields)} WHERE playerID = ?"
                    values = [row[k] for k in row if k != "playerID" and k != "source_table"] + [playerID]
                    cur.execute(update_sql, values)
            else:
                insert_fields = [k for k in row if k != "source_table"]
                insert_sql = f"INSERT INTO player ({', '.join(insert_fields)}) VALUES ({', '.join(['?' for _ in insert_fields])})"
                values = [row[k] for k in insert_fields]
                cur.execute(insert_sql, values)

            # Handle pitcher if applicable
            if "pitcher" in positions_list:
                cur.execute("SELECT playerID FROM pitcher WHERE playerID = ?", (playerID,))
                pitcher_exists = cur.fetchone()

                if pitcher_exists:
                    response = self.message.show_message(f"Would you like to overwrite {player_name} pitching stats?")
                    if response.lower() == "yes":
                        pitcher_fields = [k for k in row if k in self.pitcher_schema and k != "playerID"]
                        update_sql = f"UPDATE pitcher SET {', '.join([f'{k}=?' for k in pitcher_fields])} WHERE playerID = ?"
                        values = [row[k] for k in pitcher_fields] + [playerID]
                        cur.execute(update_sql, values)
                else:
                    pitcher_fields = [k for k in row if k in self.pitcher_schema]
                    insert_sql = f"INSERT INTO pitcher ({', '.join(pitcher_fields)}) VALUES ({', '.join(['?' for _ in pitcher_fields])})"
                    values = [row[k] for k in pitcher_fields]
                    cur.execute(insert_sql, values)

    con.commit()
    cur.close()
    con.close()
   

  # create league, team, player/pitcher instance of csv data
  def upsert_league_instance_from_csv(self, obj):
    league = League()
    self.league = league

  def upsert_team_instance_from_csv(self, obj):
    team = Team()
    self.teams.append(team)

  def upsert_player_instance_from_csv(self, obj):
    player = Player()
    pos = player.positions 
    if "pitcher" in pos:
       pitcher = Pitcher()

  def upsert_pitcher_instance_from_csv(self):
    pass
