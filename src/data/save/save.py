import csv
import os 
import sqlite3 
import json
from pathlib import Path
import random
import glob
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from datetime import datetime


class Save():
  def __init__(self, db, league, message, file_dir, selection, folder='/CSV'):
    # Convert Path objects to strings
    self.db = str(db) if db else None
    file_dir = str(file_dir) if file_dir else None
    
    print(f"Save.__init__ - Database path received: '{self.db}'")
    print(f"Save.__init__ - File directory: '{file_dir}'")
    
    # Ensure database path always ends with League.db
    if self.db and not self.db.endswith('.db'):
      print(f"Warning: Database path does not end with .db: '{self.db}'")
      self.db = f"{file_dir}/DB/League.db"
      print(f"Corrected to: '{self.db}'")
    
    self.file_dir = file_dir 
    self.folder = folder
    #self.openDB = self.open_db()
    #self.con = self.get_con()
    #self.cur = self.get_cur()
    self.league = league
    self.message = message
    self.NULL_TOKEN = "__SQL_NULL__"
    self.selection = selection
    
  def db_exists(self):
    db_path = Path(self.db)
    db_uri = f"file:{db_path}?mode=rw"
    try:
        con = sqlite3.connect(db_uri, uri=True, timeout=30)
        cur = con.cursor()
        return con, cur
    except sqlite3.OperationalError:
        print(f"Database '{db_path}' does not exist!")
        return None

  def open_db(self):
    result = self.db_exists()
    if result:
      return result  # con, cur

    # Ensure parent directory exists before creating new DB
    db_path = Path(self.db)
    db_dir = db_path.parent
    if not db_dir.exists():
        print(f"Creating missing directory: {db_dir}")
        db_dir.mkdir(parents=True, exist_ok=True)
        

    # Create new database
    print(f"Creating new database at: {self.db}")
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
    
    self.init_league()
    self.init_team()
    self.init_player()
    self.init_pitcher()

    con.commit()
    con.close()

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
          self.league.admin['Name'],
          self.league.admin['Commissioner'],
          self.league.admin['Historian'],
          self.league.admin['Recruitment'],
          self.league.admin['Communications'],
          self.league.admin['Historian'],
          self.league.admin['Start'],
          self.league.admin['Stop']
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
  
  def update_league(self, cur, con, league_ID, obj, dir_list):
    ##print(dir_list)
    cols = []
    vals = []
    ##print(exclude_attrs(team))

    for el in dir_list:
      val = getattr(obj, el)

      if isinstance(val, (dict)):
        print('league val:', val)
        keys = list(val.keys())
        values = list(val.values())
        print(keys)
        print(values)

        for indx, el in enumerate(keys):
          if values[indx] is None:
            cols.append(el.lower())
            vals.append(self.NULL_TOKEN)
          else:
            cols.append(el.lower())
            vals.append(values[indx].lower())
      
      else:
        cols.append(el)
        vals.append(val)

    #placeholders = ", ".join(["?"] * len(vals))
    #column_str = ", ".join(cols)

    set_clause = ", ".join([f"{col} = ?" for col in cols])
    sql = f"UPDATE league SET {set_clause} WHERE leagueID = ?"

    print(set_clause)
    print(sql)
    print(cols)

    # modify command
    cur.execute(sql, vals + [league_ID])
    con.commit()

  def save_league(self):
    """Upsert league row by leagueID; update admin fields if league already exists."""
    def keep_attrs(obj, flag=1):
      attrs = dir(obj)
      keep_1 = ['leagueID', 'admin']
      keep_2 = ['name', 'commissioner', 'treasurer', 'communications', 'historian', 'recruitment', 'start', 'stop']
      if flag == 1:
        dir_list = [x for x in attrs if self.sql_safe(x) and x in keep_1]  
      elif flag == 2:
        dir_list = [x for x in attrs if self.sql_safe(x) and x in keep_2]  
      return dir_list
    
    print("save league - open DB")
    con, cur = self.open_db()
    dir_list_1 = keep_attrs(self.league)

    # if there is a league table in DB
    if self.table_exists(con, cur, 'league'):
      # update league table if update flag 
      leagueID = self.league.leagueID 

      # fetch all league instances IDs
      res = cur.execute(f"SELECT leagueID FROM league")
      raw_ids = [row[0] for row in res.fetchall()] # ret of league IDs
      # Normalize both DB and in-memory IDs to ints when possible
      norm_ids = set()
      for x in raw_ids:
        try:
          norm_ids.add(int(x))
        except Exception:
          norm_ids.add(x)
      try:
        leagueID_norm = int(leagueID)
      except Exception:
        leagueID_norm = leagueID
      print(list(norm_ids))

      cols = []
      vals = []

      # if current league exists in DB
      if leagueID_norm in norm_ids:
        print(f"League {self.league.admin['Name']} (ID: {leagueID}) already exists in DB. Updating...")
        
        # Just update the existing league data (normal save behavior)
        self.update_league(cur, con, self.league.leagueID, self.league, dir_list_1)
        print("League data updated successfully.")
        return False
        
      elif leagueID_norm not in norm_ids:
        # League doesn't exist in DB, insert it
        print(f"League {self.league.admin['Name']} (ID: {leagueID}) not found in DB. Inserting...")

        for el in dir_list_1:
          val = getattr(self.league, el)

          if isinstance(val, (dict)):
            print('team val:', val)
            keys = list(val.keys())
            values = list(val.values())
            print(keys)
            print(values)

            for indx, el in enumerate(keys):
              if values[indx] is None:
                cols.append(el)
                vals.append(self.NULL_TOKEN)
              else:
                cols.append(el.lower())
                vals.append(values[indx].lower())
          
          else:
            cols.append(el)
            vals.append(val)

        # After loop completes, build INSERT statement
        placeholders = ", ".join(["?"] * len(vals))
        column_str = ", ".join(cols)

        print(f"Inserting league: {column_str}")
        print(f"Values: {vals}")
        
        try: 
          # Use upsert semantics to avoid UNIQUE conflicts on leagueID
          cur.execute(
                      f"INSERT OR REPLACE INTO league ({column_str}) VALUES ({placeholders})",
                      tuple(vals)
                    )
                  
          con.commit()
          print("League inserted successfully.")
        
        except Exception as e:
          print(f"Error-League Save: DB not updated {e}")
        
        return False
    
    # If we reach here, league was saved/updated successfully without recreating DB
    return False

  def save_team(self):
    """Persist teams to DB: insert missing teams and update existing by teamID."""
    print("save_team - Starting...")
    def keep_attrs(obj):
      keep = ['teamID', 'name', 'leagueID', 'league', 'logo', 'manager', 'players', 'lineup', 'positions', 'wins', 'losses', 'games_played', 'wl_avg', 'bat_avg', 'team_era', 'max_roster']
      dir_list = [x for x in keep if self.sql_safe(x)] 
      ##print(dir_list)
      return dir_list
    
    con, cur = self.open_db()

    if self.table_exists(con, cur, 'team'):
        print('save_team - Table "team" exists')
        
        objsTeam = self.league.get_all_objs()
        print(f'save_team - Found {len(objsTeam)} teams in league memory')

        res = cur.execute(f"SELECT teamID FROM team")
        ret = res.fetchall()
        
        # check for league name duplicate 
        if len(ret) == 0:
          print(f'save_team - No teams in DB yet, inserting {len(objsTeam)} teams...')
          for i in range(len(objsTeam)):
            ##print('team to save:', objsTeam[i].name)
            team_name = objsTeam[i].name
            team = objsTeam[i]

            '''if self.scan_ret(ret, team.teamID):
              #print('teamID already exists!')
              continue'''
            
            dir_list = keep_attrs(team) 
            #print(dir_list)
            cols = []
            vals = []
            check_type = [int, str, float, dict, list, type(None)]
            ##print(exclude_attrs(team))

            for el in dir_list:
              val = getattr(team, el)
              #print('el--val:', el, val)
              
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
            print(f'  - Inserted team: {team_name}')
            
          con.commit()
          print(f'save_team - Committed {len(objsTeam)} teams to database')

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
        print("save_team - Connection closed")
  
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
    """Persist players (and pitchers) to DB: upsert by playerID; keep roster in sync."""
    print("save_player - Starting...")
    def keep_attrs_player(obj):
      keep = ['playerID', 'name', 'leagueID', 'teamID', 'number', 'team', 'positions', 'pa', 'at_bat', 'fielder_choice', 'hit', 'bb', 'hbp', 'so', 'hr', 'rbi', 'runs', 'singles', 'doubles', 'triples', 'sac_fly', 'OBP', 'BABIP', 'SLG', 'AVG', 'ISO', 'image']
      dir_list = [x for x in keep if self.sql_safe(x)] 
      return dir_list
    
    def keep_attrs_pitcher(obj):
      keep = ['name', 'playerID', 'teamID', 'leagueID', 'wins', 'losses', 'era', 'games_played', 'games_completed', 'shutouts', 'save_ops', 'ip', 'p_at_bats', 'p_hits', 'p_runs', 'er', 'p_hb', 'p_so', 'WHIP', 'p_avg', 'k_9', 'bb_9']
      dir_raw = dir(obj)
      dir_list = [x for x in keep if self.sql_safe(x)]
      return dir_list
    
    def isPitcher(obj):
      return "pitcher" in obj.positions 
    
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
        raw_player_ids = [row[0] for row in res.fetchall()]
        norm_player_ids = set()
        for pid in raw_player_ids:
          try:
            norm_player_ids.add(int(pid))
          except Exception:
            norm_player_ids.add(pid)
          
        for player in players: 
          player_name = player.name 
          player_ID = player.playerID
          player_team_ID = player.teamID 
          checkPitcher = isPitcher(player)
          
          # does player exist in DB ???
          try:
            player_ID_norm = int(player_ID)
          except Exception:
            player_ID_norm = player_ID
          if player_ID_norm in norm_player_ids:
            print('player in DB: ', player_ID, ret)

            # is the player a pitcher?
            # if yes, update pitcher and update player tables
            if checkPitcher:
              #print('match pitcher, wish to update?')
              self.update_pitcher(con, cur, player, keep_attrs_pitcher)
              self.update_player(con, cur, player, keep_attrs_player) 
              #continue 

            else:
              # if not, update player table only
              self.update_player(con, cur, player, keep_attrs_player)
              #continue

          # if playerID not in DB, create new player
          elif player_ID_norm not in norm_player_ids:
            #print('no match player, wish to create?')

            cols = []
            vals = []

            # if player is a pitcher 
            # exclude players attrs, except name, playerID, teamID, leagueID
            if checkPitcher:
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
                    f"INSERT OR REPLACE INTO pitcher ({column_str}) VALUES ({placeholders})",
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
                f"INSERT OR REPLACE INTO player ({column_str}) VALUES ({placeholders})",
                tuple(vals)
            )
        
          con.commit()

        self.update_team_roster(con, cur, players, team_ID)

    con.close()

  def update_player(self, con, cur, player_obj, keep_func):
    """Update existing player row fields (excluding playerID) using provided attribute filter."""
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
      
      elif el == "playerID":
        continue
      
      cols.append(el)
      vals.append(val)

    #placeholders = ", ".join(["?"] * len(vals))
    #column_str = ", ".join(cols)

    set_clause = ", ".join([f"{col} = ?" for col in cols])
    sql = f"UPDATE player SET {set_clause} WHERE playerID = ?"

    print(cols)
    print(vals)
    print(sql)
    
    # modify command
    cur.execute(sql, vals + [player_ID])
    con.commit()

  def update_pitcher(self, con, cur, player_obj, keep_func):
    """Update existing pitcher row fields (excluding playerID) using provided attribute filter."""
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

      elif el == "playerID":
        continue
      
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
    """Write team's roster (names) to DB for teamID; keeps DB in step with memory."""
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

  def save_csv(self, db_path, csv_path):
    print(f"\n=== save_csv START ===")
    print(f"save_csv - Database path: {db_path}")
    print(f"save_csv - CSV export path: {csv_path}")
    
    # Verify database file exists
    if not os.path.exists(db_path):
      print(f"Error: Database file does not exist at: {db_path}")
      return
    
    try:
      con = sqlite3.connect(db_path)
      cur = con.cursor()
    except Exception as e:
      print(f"Error: Unable to connect to database '{db_path}': {e}")
      return

    '''new_dir = os.path.join(csv_path, self.get_timestamp())
    print('new dir:', new_dir)
    
    if not os.path.exists(new_dir):
      os.mkdir(new_dir)
      
    elif os.path.exists(new_dir):
      print(f"Dir: {new_dir} exists!")
      new_dir = os.path.join(csv_path, self.get_timestamp(flag=True))
      os.mkdir(new_dir)'''
    
    try: 
      cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
      tables = [row[0] for row in cur.fetchall()]
      print(f"save_csv - Found {len(tables)} tables in database: {tables}")
      
      # Check row counts for each table
      for table in tables:
        try:
          cur.execute(f"SELECT COUNT(*) FROM {table}")
          count = cur.fetchone()[0]
          print(f"  - {table}: {count} rows")
        except Exception as e:
          print(f"  - {table}: Error counting rows: {e}")
    
    except Exception as e:
      print(f'Error querying database tables: {e}')
      con.close()
      return
    
    
    # Ensure the directory exists
    try:
      for table in tables:
          cur.execute(f"SELECT * FROM {table}")
          rows = cur.fetchall()

          column_names = [description[0] for description in cur.description]

          file_name = f"{table}{self.get_timestamp()}.csv"
          file_path = os.path.join(csv_path, file_name)
          
          if self.isPathExist(file_path):
            file_name = self.avoid_dup_file_name(table, self.get_timestamp(flag=True))
            file_path = self.upd_file_path(csv_path, file_name)

          with open(file_path, "w", newline='', encoding='utf-8') as f:
              writer = csv.writer(f)
              writer.writerow(column_names)
              writer.writerows(rows)
          
          print(f"✓ Exported {table} to {file_path}")

      print("✓ All CSV files exported successfully")
    except Exception as e:
      print(f"An error occurred while exporting CSVs: {e}")
    finally:
      con.close()
  
  def isPathExist(self, file_path):
    if os.path.exists(file_path):
      return True 
    return False
  
  def avoid_dup_file_name(self, table, timestamp):
    file_name = f"{table}{timestamp}.csv"
    return file_name 
  
  def upd_file_path(self, output_path, file_name):
    file_path = os.path.join(output_path, file_name)
    return file_path

  # ------------------------------------------------------------------------------------------------- #
  # currently in use
  def save_master(self, db_path, csv_path):
    """Top-level save: ensure schema, upsert league/team/player, then export CSV if requested."""
    print("\n" + "="*60)
    print("save_master - STARTING")
    print(f"  db_path parameter: {db_path}")
    print(f"  csv_path parameter: {csv_path}")
    print(f"  self.db: {self.db}")
    print("="*60 + "\n")
    db_was_initialized = False  # Track if we created a fresh DB
    
    result = self.open_db() 
    con = cur = None
    if result:
      con, cur = result
      print('save master - con/cur:', con, cur)
    else:
      print('No League.db file! Creating new database...')
      self.init_new_db()
      db_was_initialized = True  # DB was just created with league data
      result = self.open_db()
      con, cur = result

    res = cur.execute("SELECT name from sqlite_master where type='table'")
    all_tables = [row[0] for row in res.fetchall()]
    # Filter out system tables - only check for actual data tables
    ret = [t for t in all_tables if t not in ('sqlite_sequence', 'sqlite_stat1')]

    print("save master - db fetch all:", res, all_tables)
    print(f"save master - data tables (excluding system tables): {ret}")
    if len(ret) == 0:
      print('No tables found! Creating new database...')
      con.close()  # Close old connection before creating new DB
      self.init_new_db()
      db_was_initialized = True  # DB was just created with league data
      # Reconnect after init_new_db to see the new tables
      result = self.open_db()
      con, cur = result
      print("save master - Reconnected after init_new_db")
    else:
      # Tables exist - check if there's stale data that conflicts with current save
      # This handles the case where user loaded CSV, removed from memory, then added new data
      try:
        cur.execute("SELECT leagueID FROM league")
        existing_leagues = cur.fetchall()
        if existing_leagues:
          existing_id_raw = existing_leagues[0][0]
          current_id_raw = self.league.leagueID
          # Normalize to ints when possible to avoid false mismatches due to type/format
          try:
            existing_id = int(existing_id_raw)
          except Exception:
            existing_id = existing_id_raw
          try:
            current_id = int(current_id_raw)
          except Exception:
            current_id = current_id_raw
          print(f"save master - DB has league {existing_id}, memory has league {current_id}")
          
          # If different league IDs, we need to clear and rebuild
          if existing_id != current_id:
            print("save master - League ID mismatch! Clearing DB and rebuilding...")
            # Drop all tables
            for table_name in ret:
              cur.execute(f"DROP TABLE IF EXISTS {table_name}")
            con.commit()
            con.close()
            # Rebuild database
            self.init_new_db()
            db_was_initialized = True
            result = self.open_db()
            con, cur = result
            print("save master - Database rebuilt with new league")
      except Exception as e:
        print(f"save master - Could not check for stale data: {e}")

    if 'csv' not in self.selection:
      print('save master - no CSV option - Database only')
      # Only call save_league if DB wasn't just initialized (which already inserted league)
      if not db_was_initialized:
        result = self.save_league()
        # If save_league() recreated the DB, it already has league data
        if result == True:
          db_was_initialized = True
      # Close connection before calling save_team/save_player (they open their own)
      con.close()
      # save_team() and save_player() will open, use, and close their own connections
      self.save_team()
      self.save_player()

    elif 'database' not in self.selection:
      print('save master - no DB option - CSV only')
      # Close connection before CSV export
      con.commit()
      con.close()
      self.save_csv(self.db, csv_path) 
    
    else:
      print('else option - save all (Database + CSV)')
      # Only call save_league if DB wasn't just initialized (which already inserted league)
      if not db_was_initialized:
        result = self.save_league()
        # If save_league() recreated the DB, it already has league data
        if result == True:
          db_was_initialized = True
      # Close connection before calling save_team/save_player (they open their own)
      con.close()
      # save_team() and save_player() will open, use, and close their own connections
      self.save_team()
      print("save_master - save_team() completed")
      self.save_player()
      print("save_master - save_player() completed")
      
      # Verify data was written (open a fresh connection just for verification)
      try:
          verify_con, verify_cur = self.open_db()
          verify_cur.execute("SELECT COUNT(*) FROM league")
          league_count = verify_cur.fetchone()[0]
          verify_cur.execute("SELECT COUNT(*) FROM team")
          team_count = verify_cur.fetchone()[0]
          verify_cur.execute("SELECT COUNT(*) FROM player")
          player_count = verify_cur.fetchone()[0]
          print(f"save_master - After save: league={league_count}, teams={team_count}, players={player_count}")
          verify_con.close()
      except Exception as e:
          print(f"save_master - Could not verify row counts: {e}")
      
      print("save_master - Database operations completed, now calling save_csv()")
      
      self.save_csv(self.db, csv_path)
  
  def parse_json(self, raw, fallback=None):
    try:
        return json.loads(raw) if raw else fallback
    except (json.JSONDecodeError, TypeError):
        return fallback

  def format_row(self, table_name, row, headers):
    row = list(row)

    if table_name == "team":
        for field in ["players", "lineup", "positions"]:
            if field in headers:
                idx = headers.index(field)
                parsed = self.parse_json(row[idx], [] if field == "players" else {})
                if isinstance(parsed, list):
                    row[idx] = ", ".join(parsed)
                elif isinstance(parsed, dict):
                    row[idx] = "; ".join(f"{k}: {v}" for k, v in parsed.items())
                else:
                    row[idx] = "Invalid"

    elif table_name == "player":
        if "positions" in headers:
            idx = headers.index("positions")
            parsed = self.parse_json(row[idx], [])
            row[idx] = ", ".join(parsed) if isinstance(parsed, list) else "Invalid"

    return row

  def get_rand(self):
        rand = str(random.randint(1, 1000))
        return rand
    
  def get_timestamp(self, flag=False):
    now = datetime.now()
    date = now.strftime("_%m%d%Y")
    if flag: 
      date = now.strftime("_%m%d%Y_%S")
    #print(f"Formatted date: {date}")
    return date

                                              # ----------------------------------------------------------------------------------------- #
                                              # --------------------- outsie of class - helper init db functions -----------------------  #



def db_exists(db_path):
    """Return (con, cur) if SQLite DB exists at path; otherwise return None."""
    db_path = Path(db_path)
    db_uri = f"file:{db_path}?mode=rw"
    try:
        con = sqlite3.connect(db_uri, uri=True, timeout=60)
        cur = con.cursor()
        return con, cur
    except sqlite3.OperationalError:
        print(f"Database '{db_path}' does not exist!")
        return None

def open_db(db_path):
    """Open (or create directory then open) SQLite DB at path and return (con, cur)."""
    result = db_exists(db_path)
    if result:
        return result  # con, cur

    # Ensure parent directory exists before creating new DB
    db_path = Path(db_path)
    db_dir = db_path.parent
    if not db_dir.exists():
        print(f"Creating missing directory: {db_dir}")
        db_dir.mkdir(parents=True, exist_ok=True)

    # Create new database
    print(f"Creating new database at: {db_path}")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    return con, cur

def init_league(db_path, league):
      """Create league table if missing and insert initial league admin row."""
      con, cur = open_db(db_path)
      
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
          league.leagueID,
          league.admin['Name'],
          league.admin['Commissioner'],
          league.admin['Historian'],
          league.admin['Recruitment'],
          league.admin['Communications'],
          league.admin['Historian'],
          league.admin['Start'],
          league.admin['Stop']
      ))

      # commit created tables and close
      con.commit()
      con.close()
    # call init league

def init_team(db_path):
      """Create team table and supporting index if missing; no row insert here."""
      con, cur = open_db(db_path)

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

def init_player(db_path):
      """Create player table and unique index if missing; schema includes derived stats."""
      con, cur = open_db(db_path)
      
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

def init_pitcher(db_path):
      """Create pitcher table and unique index if missing; schema stores pitching stats."""
      # Create pitcher table
      con, cur = open_db(db_path)
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

def init_new_db(db_path, league):
  """Initialize a fresh DB schema (league/team/player/pitcher) with initial league row."""
  # Enable foreign key constraints
  con, cur = open_db(db_path)
  cur.execute("PRAGMA foreign_keys = ON")

  init_league(db_path, league)
  init_team(db_path)
  init_player(db_path)
  init_pitcher(db_path)

  con.commit()
  con.close()