import os
import sys
import re
import glob
import csv
import sqlite3
import json
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from src.data.save.save import init_new_db
from src.core.stack import InstanceStack
from src.core.game import Game 
from src.core.linked_list import LinkedList 
from src.core.player import Player, Pitcher 
from src.core.team import Team

# Map table names to their primary key
PRIMARY_KEYS = {
    "team": "teamID",
    "player": "playerID",
    "pitcher": "playerID",
    "league": "leagueID"
}

ALLOWED_TABLES = {"league", "team", "player", "pitcher"}

# Non-derived numeric fields to add during merge; derived will be recalculated
PLAYER_NUMERIC_ADD = {"pa","at_bat","fielder_choice","hit","bb","hbp","put_out","so","hr","rbi","runs","singles","doubles","triples","sac_fly"}
PLAYER_DERIVED = {"OBP","BABIP","SLG","AVG","ISO"}

PITCHER_NUMERIC_ADD = {"wins","losses","games_played","games_started","games_completed","shutouts","saves","save_ops","ip","p_at_bats","p_hits","p_runs","er","p_hr","p_hb","p_bb","p_so"}
PITCHER_DERIVED = {"WHIP","p_avg","k_9","bb_9","era"}

def _to_int(val):
    """Return val coerced to int; tolerate strings/floats/None by returning 0 on failure."""
    try:
        if val is None or val == "":
            return 0
        if isinstance(val, (int,)):
            return val
        if isinstance(val, float):
            return int(val)
        s = str(val).strip().strip('"').strip("'")
        if s == "":
            return 0
        if "." in s:
            f = float(s)
            return int(f)
        return int(s)
    except Exception:
        return 0

def _normalize_numeric_attrs(obj, fields):
    """Coerce listed numeric attributes on obj to ints in-place to ensure arithmetic safety."""
    try:
        for f in fields:
            if hasattr(obj, f):
                setattr(obj, f, _to_int(getattr(obj, f)))
    except Exception:
        pass


# ----------------------- Path Migration -----------------------
def migrate_image_path(old_path):
    """
    Migrate old image paths (Saved/Images/) to new paths (data/images/).
    
    Args:
        old_path: Image path string (may be old or new format)
        
    Returns:
        Updated path string pointing to data/images/, or None if path is invalid
    """
    if not old_path or old_path in (0, '0', 0.0, '0.0', '', None):
        return None
    
    path_str = str(old_path)
    
    # If path contains old Saved/Images structure, migrate it
    if 'Saved/Images' in path_str or 'Saved\\Images' in path_str:
        # Extract just the filename
        filename = os.path.basename(path_str)
        # Build new path
        new_path = os.path.join(os.getcwd(), 'data', 'images', filename)
        print(f"Migrating image path: {old_path} -> {new_path}")
        return new_path
    
    # If path is already in new format or is just a filename, ensure it points to data/images
    if not path_str.startswith('/') and not path_str.startswith('data/'):
        filename = os.path.basename(path_str)
        new_path = os.path.join(os.getcwd(), 'data', 'images', filename)
        return new_path
    
    # Path is already in new format
    return path_str


# ----------------------- Dialogs -----------------------
class SessionChoiceDialog(QDialog):
    """Dialog to select a CSV session."""

    def __init__(self, sessions: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select CSV Import Session")
        self.choice = None
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.setSizeGripEnabled(True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel("Multiple CSV save sessions found.\nSelect one to import:")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        main_layout.addWidget(title_label)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        for session in sorted(sessions.keys()):
            btn = QPushButton(f"Session {session} ({len(sessions[session])} files)")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked=False, s=session: self.choose(s))
            scroll_layout.addWidget(btn)

        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll, stretch=1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(self.reject)
        main_layout.addWidget(cancel_btn, alignment=Qt.AlignCenter)

    def choose(self, session: str):
        self.choice = session
        self.accept()


class DatabaseChoiceDialog(QDialog):
    """Dialog to choose new DB or update existing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database Choice")
        self.choice = None
        self.setMinimumWidth(400)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel(
            "Do you want to create a new database or update an existing one?"
        ))

        button_layout = QHBoxLayout()
        new_db_btn = QPushButton("Create New Database")
        update_btn = QPushButton("Update Existing Database")
        cancel_btn = QPushButton("Cancel")

        new_db_btn.setMinimumHeight(40)
        update_btn.setMinimumHeight(40)
        cancel_btn.setMinimumHeight(40)

        new_db_btn.clicked.connect(self.choose_new_db)
        update_btn.clicked.connect(self.choose_update)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(new_db_btn)
        button_layout.addWidget(update_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def choose_new_db(self):
        self.choice = "new database"
        self.accept()

    def choose_update(self):
        self.choice = "update existing"
        self.accept()


class OverwriteDialog(QDialog):
    """Dialog to choose overwrite, skip, or cancel when updating DB."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV Import Confirmation")
        self.choice = "cancel"
        self.setMinimumWidth(400)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel(
            "Do you want to overwrite existing data in ALL database tables?\n\n"
            "Yes = Overwrite/Update existing rows\n"
            "No = Skip rows that already exist\n"
            "Cancel = Cancel all CSV imports"
        ))

        button_layout = QHBoxLayout()
        yes_btn = QPushButton("Yes")
        no_btn = QPushButton("No")
        cancel_btn = QPushButton("Cancel")

        yes_btn.setMinimumHeight(40)
        no_btn.setMinimumHeight(40)
        cancel_btn.setMinimumHeight(40)

        yes_btn.clicked.connect(self.choose_overwrite)
        no_btn.clicked.connect(self.choose_skip)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(yes_btn)
        button_layout.addWidget(no_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def choose_overwrite(self):
        self.choice = "overwrite"
        self.accept()

    def choose_skip(self):
        self.choice = "skip"
        self.accept()


class ReplaceMergeDialog(QDialog):
    """Dialog to choose Replace (drop and reload) or Merge (upsert/additive)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Strategy")
        self.choice = "cancel"
        self.setMinimumWidth(400)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel(
            "You selected to update the existing database.\n\n"
            "Choose how to apply CSV data:\n"
            "- Replace: Drop all DB data, then load CSVs (fresh).\n"
            "- Merge: Keep DB data, add new rows, and add numeric stats to existing rows."
        ))

        button_layout = QHBoxLayout()
        replace_btn = QPushButton("Replace")
        merge_btn = QPushButton("Merge")
        cancel_btn = QPushButton("Cancel")

        replace_btn.setMinimumHeight(40)
        merge_btn.setMinimumHeight(40)
        cancel_btn.setMinimumHeight(40)

        replace_btn.clicked.connect(self.choose_replace)
        merge_btn.clicked.connect(self.choose_merge)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(replace_btn)
        button_layout.addWidget(merge_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def choose_replace(self):
        self.choice = "replace"
        self.accept()

    def choose_merge(self):
        self.choice = "merge"
        self.accept()

class SummaryDialog(QDialog):
    """Dialog to show CSV import summary."""

    def __init__(self, summary: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV Import Summary")
        self.setMinimumWidth(400)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        total_inserted = sum(v["inserted"] for v in summary.values())
        total_skipped = sum(v["skipped"] for v in summary.values())
        total_overwritten = sum(v["overwritten"] for v in summary.values())

        layout.addWidget(QLabel("<b>CSV Import Results:</b>"))

        for table, stats in summary.items():
            if stats.get("error", False):
                layout.addWidget(QLabel(f"⚠️ {table}: Skipped (table missing or no matching columns)"))
            else:
                layout.addWidget(QLabel(
                    f"✅ {table}: {stats['inserted']} inserted, "
                    f"{stats['skipped']} skipped, "
                    f"{stats['overwritten']} overwritten"
                ))

        layout.addWidget(QLabel("<hr>"))
        layout.addWidget(QLabel(
            f"<b>Total:</b> {total_inserted} inserted, "
            f"{total_skipped} skipped, "
            f"{total_overwritten} overwritten"
        ))

        ok_btn = QPushButton("OK")
        ok_btn.setMinimumHeight(35)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)




# ----------------------- CSV Loader Utilities -----------------------
def get_csv_files(directory: str) -> list:
    """Recursively collect .csv files under directory; used to assemble a load session."""
    # Search recursively to include session subfolders like CSV/save_1/*.csv
    return glob.glob(os.path.join(directory, "**", "*.csv"), recursive=True)


def group_csv_by_session(csv_files: list) -> dict:
    """Group CSVs by session key derived from filename; ignore non-data/system files."""
    """Group CSV files by session timestamp, ignore sqlite_sequence."""
    session_pattern = re.compile(
        r"^(league|team|player|pitcher)_([0-9]+(?:\([0-9]+\))?)\.csv$", re.IGNORECASE
    )
    sessions = {}
    for f in csv_files:
        filename = os.path.basename(f)
        if filename.startswith("sqlite_sequence"):
            continue
        match = session_pattern.match(filename)
        if match:
            table, session = match.groups()
            table = table.lower()
            if table in ALLOWED_TABLES:
                sessions.setdefault(session, []).append((table, f))
    return sessions


def insert_csv_to_table(table: str, csv_path: str, conn: sqlite3.Connection, mode: str, summary: dict, stack: InstanceStack, parent, league: LinkedList):
    """Insert/update table from a CSV file using mode (overwrite/skip/merge); collect instances."""
    """Insert CSV into SQLite table according to mode: overwrite/skip/merge.

    - overwrite: INSERT OR REPLACE entire rows
    - skip: INSERT only if not exists
    - merge: if row exists, add numeric fields and replace non-numeric; else INSERT
    """
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    table_columns = [info[1] for info in cursor.fetchall()]
    # use the provided league instance so teams/players accumulate across tables

    print('table cols: ', table_columns)

    if not table_columns:
        summary[table] = {"inserted": 0, "skipped": 0, "overwritten": 0, "error": True}
        return

    primary_key = PRIMARY_KEYS.get(table)
    inserted = skipped = overwritten = 0

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        valid_columns = [col for col in reader.fieldnames if col in table_columns]
        placeholders = ", ".join(["?"] * len(valid_columns))

        print('valid cols: ', valid_columns)

        for row in reader:
            values = [row.get(col, None) for col in valid_columns]
            
            print("csv values: ", values)
            #print("row in reader-fields: ", row)
            #print("table hint - instance type: ", table_hint)
            
            if mode == "overwrite":
                # Check if row exists to distinguish insert vs replace
                existed = False
                if primary_key and primary_key in valid_columns:
                    pk_value = row.get(primary_key)
                    cursor.execute(f"SELECT 1 FROM {table} WHERE {primary_key} = ?", (pk_value,))
                    existed = cursor.fetchone() is not None
                
                cursor.execute(f"INSERT OR REPLACE INTO {table} ({', '.join(valid_columns)}) VALUES ({placeholders})", values)

                if existed:
                    overwritten += 1
                else:
                    inserted += 1

                # collect ordered row aligned to valid_columns and annotate table
                ordered = {col: row.get(col, None) for col in valid_columns}
                stack.add(table, ordered, values)

            elif mode == "skip":
                if primary_key and primary_key in valid_columns:
                    pk_value = row.get(primary_key)
                    cursor.execute(f"SELECT 1 FROM {table} WHERE {primary_key} = ?", (pk_value,))
                    if cursor.fetchone():
                        skipped += 1
                        continue
                cursor.execute(f"INSERT INTO {table} ({', '.join(valid_columns)}) VALUES ({placeholders})", values)
                inserted += 1

                # collect ordered row aligned to valid_columns and annotate table
                ordered = {col: row.get(col, None) for col in valid_columns}
                stack.add(table, ordered, values)

            elif mode == "merge":
                existed = False
                row_dict = {col: row.get(col, None) for col in valid_columns}
                if primary_key and primary_key in valid_columns:
                    pk_value = row.get(primary_key)
                    cursor.execute(f"SELECT {', '.join(valid_columns)} FROM {table} WHERE {primary_key} = ?", (pk_value,))
                    existing_row = cursor.fetchone()
                    if existing_row is not None:
                        existed = True
                        existing_map = {col: existing_row[idx] for idx, col in enumerate(valid_columns)}
                        # Merge: numeric add, non-numeric replace
                        merged = {}
                        for col in valid_columns:
                            new_val = row_dict.get(col)
                            old_val = existing_map.get(col)
                            if col == primary_key:
                                merged[col] = old_val if old_val is not None else new_val
                                continue
                            # Table-specific rules
                            if table == "player":
                                if col in PLAYER_DERIVED:
                                    merged[col] = old_val  # skip; will recalc later
                                elif col in PLAYER_NUMERIC_ADD:
                                    merged[col] = _to_int(old_val) + _to_int(new_val)
                                else:
                                    merged[col] = new_val if new_val not in ('__SQL_NULL__',) else old_val
                            elif table == "pitcher":
                                if col in PITCHER_DERIVED:
                                    merged[col] = old_val
                                elif col in PITCHER_NUMERIC_ADD:
                                    merged[col] = _to_int(old_val) + _to_int(new_val)
                                else:
                                    merged[col] = new_val if new_val not in ('__SQL_NULL__',) else old_val
                            else:
                                # default behavior: replace
                                merged[col] = new_val if new_val not in ('__SQL_NULL__',) else old_val
                        # Build UPDATE statement
                        update_cols = [c for c in valid_columns if c != primary_key]
                        update_clause = ", ".join([f"{c} = ?" for c in update_cols])
                        update_vals = [merged[c] for c in update_cols] + [merged[primary_key]]
                        cursor.execute(f"UPDATE {table} SET {update_clause} WHERE {primary_key} = ?", update_vals)
                        overwritten += 1
                    else:
                        # Row not exists -> INSERT
                        cursor.execute(f"INSERT INTO {table} ({', '.join(valid_columns)}) VALUES ({placeholders})", values)
                        inserted += 1
                else:
                    # No primary key definition -> fall back to insert
                    cursor.execute(f"INSERT INTO {table} ({', '.join(valid_columns)}) VALUES ({placeholders})", values)
                    inserted += 1

                # collect ordered row for GUI building
                ordered = {col: row.get(col, None) for col in valid_columns}
                stack.add(table, ordered, values)

    conn.commit()
    summary[table] = {"inserted": inserted, "skipped": skipped, "overwritten": overwritten, "error": False}
    
    
    # Defer building GUI until all tables are processed. Instances
    # will be collected across calls via the shared InstanceStack.

def load_all_gui(instances, parent, league, mode=None):
    """Materialize league/team/player/pitcher from collected instances and refresh GUI once."""
    # Process in deterministic order: league -> team -> player -> pitcher
    league_items = []
    team_items = []
    player_items = []
    pitcher_items = []

    for item in instances:
        key = list(item.keys()).pop()
        if key == 'league':
            league_items.append(item)
        elif key == 'team':
            team_items.append(item)
        elif key == 'player':
            player_items.append(item)
        elif key == 'pitcher':
            pitcher_items.append(item)

    # League
    for item in league_items:
        vals = list(item.values()).pop()
        for el in vals:
            attr = el[0]
            val = el[1]
            if val == '__SQL_NULL__':
                continue
            load_league_gui(attr, val, league)

    # Teams
    for item in team_items:
        vals = list(item.values()).pop()
        team = Team(league, 'team', 'manager')
        for el in vals:
            attr = el[0]
            val = el[1]
            if attr in ('players',):
                continue
            elif attr in ('lineup', 'positions'):
                # parse JSON if string
                try:
                    parsed = json.loads(val) if isinstance(val, str) else val
                except Exception:
                    parsed = val
                load_team_gui(attr, parsed, team)
            elif attr == 'logo':
                # Keep logo as string path - GUI will convert to QIcon when displaying
                # Migrate old Saved/Images paths to new data/images paths
                migrated_path = migrate_image_path(val)
                if migrated_path:
                    load_team_gui(attr, migrated_path, team)
                else:
                    team.logo = None
            elif attr in ('teamID', 'leagueID'):
                # normalize numeric ids (handle '01', '1 ', '1.0')
                def _normalize_id_local(v):
                    try:
                        return int(v)
                    except Exception:
                        pass
                    try:
                        s = str(v).strip().strip('"').strip("'")
                        if '.' in s:
                            f = float(s)
                            if f.is_integer():
                                return int(f)
                        if s.isdigit():
                            return int(s)
                        return s
                    except Exception:
                        return v
                norm = _normalize_id_local(val)
                load_team_gui(attr, norm, team)
            else:
                if val in (0, '0', 0.0, '0.0'):
                    continue
                load_team_gui(attr, val, team)
        # Merge with existing team if present; otherwise add as new
        try:
            existing_team = None
            # Prefer match by teamID if set
            if hasattr(team, 'teamID') and getattr(team, 'teamID', None) not in (None, ''):
                try:
                    existing_team = league.find_teamID(team.teamID)
                except Exception:
                    existing_team = None
            # Fallback to name-based match
            if existing_team is None and hasattr(team, 'name') and team.name:
                try:
                    existing_team = league.find_team(team.name)
                except Exception:
                    existing_team = None

            if existing_team is not None:
                # Update attributes on existing team
                for el in vals:
                    attr_u = el[0]
                    val_u = el[1]
                    if attr_u in ('players',):
                        continue
                    if attr_u in ('lineup', 'positions'):
                        try:
                            parsed_u = json.loads(val_u) if isinstance(val_u, str) else val_u
                        except Exception:
                            parsed_u = val_u
                        setattr(existing_team, attr_u, parsed_u)
                    elif attr_u == 'logo':
                        migrated_path_u = migrate_image_path(val_u)
                        setattr(existing_team, attr_u, migrated_path_u if migrated_path_u else None)
                    else:
                        if val_u in (0, '0', 0.0, '0.0'):
                            continue
                        setattr(existing_team, attr_u, val_u)
            else:
                league.add_team(team)
        except Exception as e:
            print(f"Team merge/add error: {e}")
    print('league after load', league)
    print('league after load', league.view_all())
    print(f'Team count: {len(league.teams)}')

    # Build quick-lookup maps for teams
    def _norm_name(s):
        try:
            return str(s).strip().lower()
        except Exception:
            return s
    team_name_map = { _norm_name(t.name): t for t in league.get_all_objs() }
    team_id_map = { str(getattr(t, 'teamID', '')).strip(): t for t in league.get_all_objs() }

    # Helper: normalize ids from CSV and robust team resolve by ID or name
    def _normalize_id(v):
        if v is None:
            return None
        try:
            return int(v)
        except Exception:
            pass
        try:
            s = str(v).strip().strip('"').strip("'")
            if '.' in s:
                f = float(s)
                if f.is_integer():
                    return int(f)
            # JSON numeric
            try:
                j = json.loads(s)
                if isinstance(j, (int, float)):
                    jf = float(j)
                    return int(jf) if jf.is_integer() else s
            except Exception:
                pass
            if s.isdigit():
                return int(s)
            return s
        except Exception:
            return v

    def _resolve_team_by_id_or_name(id_val, name_val):
        # Try by ID first
        if id_val is not None:
            norm_id = _normalize_id(id_val)
            if isinstance(norm_id, int):
                found = league.find_teamID(norm_id)
                if found is not None:
                    return found
            # fallback: compare as strings
            try:
                target = str(norm_id if norm_id is not None else id_val).strip()
                if target in team_id_map:
                    return team_id_map[target]
            except Exception:
                pass
        # Try by name next
        if name_val:
            try:
                by_map = team_name_map.get(_norm_name(name_val))
                if by_map:
                    return by_map
                return league.find_team(name_val)
            except Exception:
                return None
        return None

    # Players
    for item in player_items:
        vals = list(item.values()).pop()
        # Temporary minimal team placeholder; will reassign to real team
        team_sample = Team(league, "team sample", "manager")
        player = Player('player', 0, team_sample, league)
        find_team = None
        fallback_team_name = None
        captured_player_id = None
        pending_team_id = None
        parsed_positions = []
        for el in vals:
            attr = el[0]
            val = el[1]
            if attr == 'positions':
                # parse positions JSON
                try:
                    parsed = json.loads(val) if isinstance(val, str) else val
                except Exception:
                    parsed = val
                load_player_gui(attr, parsed, player)
                try:
                    parsed_positions = list(parsed)
                except Exception:
                    parsed_positions = []
            elif attr == 'teamID':
                # store as int if possible
                try:
                    pending_team_id = int(val)
                except Exception:
                    pending_team_id = val
                # also set attribute with normalized int
                try:
                    load_player_gui(attr, int(val), player)
                except Exception:
                    load_player_gui(attr, val, player)
            elif attr == 'playerID':
                try:
                    captured_player_id = int(val)
                    load_player_gui(attr, captured_player_id, player)
                except Exception:
                    captured_player_id = val
                    load_player_gui(attr, val, player)
            elif attr == 'team':
                fallback_team_name = val
                # DON'T set player.team to the string - we'll set it later after resolving the Team object
            elif attr == 'image':
                # Keep image as string path for player - stat dialog handles conversion
                # Don't convert to QIcon here, just store the path
                # Migrate old Saved/Images paths to new data/images paths
                migrated_path = migrate_image_path(val)
                if migrated_path:
                    player.image = migrated_path
                else:
                    player.image = None
            else:
                if val in (0, '0', 0.0, '0.0'):
                    continue
                # Convert numeric stats to proper types when loading from CSV
                if attr in PLAYER_NUMERIC_ADD:
                    load_player_gui(attr, _to_int(val), player)
                elif attr in PLAYER_DERIVED:
                    try:
                        load_player_gui(attr, float(val) if val not in (0, '0', 0.0, '0.0', '', None) else 0.0, player)
                    except Exception:
                        load_player_gui(attr, 0.0, player)
                else:
                    load_player_gui(attr, val, player)
        # resolve team after reading all attrs: by name first per requirement, then by ID
        if fallback_team_name:
            try:
                # prefer map for case-insensitive/trim matches
                find_team = team_name_map.get(_norm_name(fallback_team_name)) or league.find_team(fallback_team_name)
            except Exception:
                find_team = None
        if find_team is None and pending_team_id is not None:
            find_team = _resolve_team_by_id_or_name(pending_team_id, None)
        
        # Validate and set team FIRST, before any type conversions
        if find_team is not None:
            # Validate that find_team is actually a Team object, not a string
            if isinstance(find_team, str):
                print(f"ERROR: find_team is a string '{find_team}' instead of a Team object for player {getattr(player, 'name', 'unknown')}")
                print(f"  fallback_team_name: {fallback_team_name}")
                print(f"  pending_team_id: {pending_team_id}")
                find_team = None  # Set to None so it's handled below
            
            if find_team is not None:
                # Set team references on player first
                player.team = find_team
                player.teamID = find_team.teamID
                player.league = league
                player.leagueID = league.leagueID
                
                # NOW convert to Pitcher if needed (after team is set properly)
                if 'pitcher' in parsed_positions:
                    temp = player
                    pitcher_player = Pitcher(temp.name, temp.number, temp.team, temp.league, positions=parsed_positions)
                    # copy offense stats and ids
                    for k in ['pa','at_bat','fielder_choice','hit','bb','hbp','put_out','so','hr','rbi','runs','singles','doubles','triples','sac_fly','OBP','BABIP','SLG','AVG','ISO','image','playerID','leagueID','teamID']:
                        setattr(pitcher_player, k, getattr(temp, k, getattr(pitcher_player, k, 0)))
                    player = pitcher_player
            else:
                print(f"Warning: team not found for player {getattr(player, 'name', '')} (after validation)")
                continue  # Skip this player
            exists = False
            pid = getattr(player, 'playerID', None)
            for existing in find_team.players:
                if pid is not None and getattr(existing, 'playerID', None) == pid:
                    exists = True
                    break
                if pid is None and existing.name == player.name:
                    exists = True
                    break
            if not exists:
                find_team.add_player(player)
            else:
                # Merge behavior using model setters to honor stat logic
                if mode == 'merge':
                    # Ensure message pipe exists for validations/warnings
                    try:
                        if getattr(existing, 'message', None) is None:
                            if hasattr(parent, 'message') and getattr(parent, 'message', None) is not None:
                                existing.message = parent.message
                            else:
                                class _Msg:
                                    def show_message(self, m):
                                        print(f"[MESSAGE] {m}")
                                existing.message = _Msg()
                    except Exception:
                        pass
                    # Normalize existing numeric fields to integers to avoid str concatenation
                    _normalize_numeric_attrs(existing, [
                        'pa','at_bat','fielder_choice','hit','bb','hbp','put_out','so','hr','rbi','runs','singles','doubles','triples','sac_fly'
                    ])
                    # Apply in logical, conflict-free order
                    ordered_sets = [
                        # 1) Hits headline first
                        ('hit', 'set_hit'),
                        # 2) Components bounded by hits
                        ('singles', 'set_singles'), ('doubles', 'set_doubles'), ('triples', 'set_triples'), ('hr', 'set_hr'),
                        # 3) PA non-AB events
                        ('bb', 'set_bb'), ('hbp', 'set_hbp'), ('fielder_choice', 'set_fielder_choice'),
                        # 4) Outs affecting AB/PA
                        ('so', 'set_so'), ('sac_fly', 'set_sac_fly'),
                        # 5) Cosmetic/counters
                        ('rbi', 'set_rbi'), ('runs', 'set_runs')
                    ]
                    for attr_name, setter_name in ordered_sets:
                        try:
                            delta = _to_int(getattr(player, attr_name, 0))
                            if delta:
                                setter = getattr(existing, setter_name, None)
                                if callable(setter):
                                    setter(delta)
                                else:
                                    setattr(existing, attr_name, _to_int(getattr(existing, attr_name, 0)) + delta)
                        except Exception as e:
                            try:
                                print(f"[MERGE][PLAYER] Failed {attr_name}: delta={delta} name={getattr(existing,'name',None)} id={getattr(existing,'playerID',None)} team={getattr(find_team,'name',None)} pa={getattr(existing,'pa',None)} ab={getattr(existing,'at_bat',None)} hit={getattr(existing,'hit',None)} error={e}")
                            except Exception:
                                pass
                            try:
                                if hasattr(parent, 'message') and getattr(parent, 'message', None) is not None:
                                    parent.message.show_message(f"Merge warning for {getattr(existing,'name','player')}: could not merge {attr_name}.", btns_flag=False, timeout_ms=2000)
                            except Exception:
                                pass
                    # Recalculate derived offense metrics
                    try:
                        if hasattr(existing, 'set_AVG'): existing.set_AVG()
                        if hasattr(existing, 'set_SLG'): existing.set_SLG()
                        if hasattr(existing, 'set_BABIP'): existing.set_BABIP()
                        if hasattr(existing, 'set_OBP'): existing.set_OBP()
                        if hasattr(existing, 'set_ISO'): existing.set_ISO()
                    except Exception:
                        pass
        else:
            print(f"Warning: team not found for player {getattr(player, 'name', '')} (teamID/team name mismatch)")

    # Pitchers
    for item in pitcher_items:
        vals = list(item.values()).pop()
        # Create a temporary placeholder team object to initialize the pitcher
        temp_team = Team(league, 'placeholder', 'manager')
        pitcher = Pitcher('pitcher', 0, temp_team, league)
        find_team = None
        fallback_team_name = None
        captured_player_id = None
        pending_team_id = None
        for el in vals:
            attr = el[0]
            val = el[1]
            if attr == 'teamID':
                try:
                    pending_team_id = int(val)
                    load_player_gui(attr, pending_team_id, pitcher)
                except Exception:
                    pending_team_id = val
                    load_player_gui(attr, val, pitcher)
            elif attr == 'playerID':
                try:
                    captured_player_id = int(val)
                except Exception:
                    captured_player_id = val
                load_player_gui(attr, captured_player_id, pitcher)
            elif attr == 'team':
                fallback_team_name = val
                # DON'T set pitcher.team to the string - we'll set it later after resolving the Team object
            elif attr == 'image':
                # Keep image as string path for pitcher - stat dialog handles conversion
                # Migrate old Saved/Images paths to new data/images paths
                migrated_path = migrate_image_path(val)
                if migrated_path:
                    pitcher.image = migrated_path
                else:
                    pitcher.image = None
            else:
                if val in (0, '0', 0.0, '0.0'):
                    continue 
                # Convert numeric stats to proper types when loading from CSV
                if attr in PITCHER_NUMERIC_ADD:
                    load_pitcher_gui(attr, _to_int(val), pitcher)
                elif attr in PITCHER_DERIVED:
                    try:
                        load_pitcher_gui(attr, float(val) if val not in (0, '0', 0.0, '0.0', '', None) else 0.0, pitcher)
                    except Exception:
                        load_pitcher_gui(attr, 0.0, pitcher)
                else:
                    load_pitcher_gui(attr, val, pitcher)
        # resolve team after reading all attrs: by name first per requirement, then by ID
        if fallback_team_name:
            try:
                find_team = team_name_map.get(_norm_name(fallback_team_name)) or league.find_team(fallback_team_name)
            except Exception:
                find_team = None
        if find_team is None and pending_team_id is not None:
            find_team = _resolve_team_by_id_or_name(pending_team_id, None)
        
        # Validate that find_team is actually a Team object, not a string
        if find_team is not None and isinstance(find_team, str):
            print(f"ERROR: find_team is a string '{find_team}' instead of a Team object for pitcher {getattr(pitcher, 'name', 'unknown')}")
            print(f"  fallback_team_name: {fallback_team_name}")
            print(f"  pending_team_id: {pending_team_id}")
            find_team = None
        
        if find_team is not None:
            # If a matching player already exists, upgrade/merge
            existing_index = None
            existing_player = None
            if captured_player_id is not None:
                for idx, p in enumerate(find_team.players):
                    if getattr(p, 'playerID', None) == captured_player_id:
                        existing_index = idx
                        existing_player = p
                        break
            if existing_player is not None:
                # Preserve offense stats and identity, replace with Pitcher subtype if needed
                if not isinstance(existing_player, Pitcher):
                    new_pitcher = Pitcher(existing_player.name, existing_player.number, find_team, league, positions=existing_player.positions)
                    # copy offensive stats
                    for k in ['pa','at_bat','fielder_choice','hit','bb','hbp','put_out','so','hr','rbi','runs','singles','doubles','triples','sac_fly','OBP','BABIP','SLG','AVG','ISO','image','playerID','leagueID','teamID']:
                        setattr(new_pitcher, k, getattr(existing_player, k, getattr(new_pitcher, k, 0)))
                    # merge/replace pitcher stats using setters
                    if mode == 'merge':
                        # Ensure message pipe exists
                        try:
                            if getattr(new_pitcher, 'message', None) is None:
                                if hasattr(parent, 'message') and getattr(parent, 'message', None) is not None:
                                    new_pitcher.message = parent.message
                                else:
                                    class _Msg:
                                        def show_message(self, m):
                                            print(f"[MESSAGE] {m}")
                                    new_pitcher.message = _Msg()
                        except Exception:
                            pass
                        # Normalize numeric fields on new_pitcher before merge
                        _normalize_numeric_attrs(new_pitcher, [
                            'wins','losses','games_played','games_started','games_completed','shutouts','saves','save_ops','ip','p_at_bats','p_hits','p_runs','er','p_hr','p_hb','p_bb','p_so'
                        ])
                        # Apply in logical order to avoid cap conflicts
                        pitcher_setters = [
                            # 1) Game frame
                            ('games_played','set_games_played'), ('wins','set_wins'), ('losses','set_losses'),
                            ('games_started','set_games_started'), ('games_completed','set_games_completed'),
                            ('shutouts','set_shutouts'), ('saves','set_saves'), ('save_ops','set_save_ops'),
                            # 2) Batter-facing totals first
                            ('p_at_bats','set_p_at_bats'),
                            # 3) Components bounded by p_at_bats
                            ('p_hits','set_p_hits'), ('p_bb','set_p_bb'), ('p_so','set_p_so'), ('p_hr','set_p_hr'), ('p_hb','set_p_hb'), ('p_runs','set_p_runs'), ('er','set_er'),
                            # 4) Innings last
                            ('ip','set_ip')
                        ]
                        for attr_name, setter_name in pitcher_setters:
                            try:
                                delta = _to_int(getattr(pitcher, attr_name, 0))
                                if delta:
                                    setter = getattr(new_pitcher, setter_name, None)
                                    if callable(setter):
                                        setter(delta)
                                    else:
                                        setattr(new_pitcher, attr_name, _to_int(getattr(new_pitcher, attr_name, 0)) + delta)
                            except Exception as e:
                                try:
                                    print(f"[MERGE][PITCHER->NEW] Failed {attr_name}: delta={delta} name={getattr(new_pitcher,'name',None)} id={getattr(new_pitcher,'playerID',None)} team={getattr(find_team,'name',None)} ip={getattr(new_pitcher,'ip',None)} p_ab={getattr(new_pitcher,'p_at_bats',None)} error={e}")
                                except Exception:
                                    pass
                                try:
                                    if hasattr(parent, 'message') and getattr(parent, 'message', None) is not None:
                                        parent.message.show_message(f"Merge warning for {getattr(new_pitcher,'name','pitcher')}: could not merge {attr_name}.", btns_flag=False, timeout_ms=2000)
                                except Exception:
                                    pass
                    else:
                        for k in ['wins','losses','games_played','games_started','games_completed','shutouts','saves','save_ops','ip','p_at_bats','p_hits','p_runs','er','p_hr','p_hb','p_bb','p_so','WHIP','p_avg','k_9','bb_9']:
                            setattr(new_pitcher, k, getattr(pitcher, k, getattr(new_pitcher, k, 0)))
                    # ensure positions includes pitcher
                    try:
                        if 'pitcher' not in new_pitcher.positions:
                            new_pitcher.positions.append('pitcher')
                    except Exception:
                        pass
                    # recalc derived pitching
                    try:
                        if hasattr(new_pitcher, 'set_era'): new_pitcher.set_era()
                        if hasattr(new_pitcher, 'set_WHIP'): new_pitcher.set_WHIP()
                        if hasattr(new_pitcher, 'set_p_avg'): new_pitcher.set_p_avg()
                        if hasattr(new_pitcher, 'set_k_9'): new_pitcher.set_k_9()
                        if hasattr(new_pitcher, 'set_bb_9'): new_pitcher.set_bb_9()
                    except Exception:
                        pass
                    find_team.players[existing_index] = new_pitcher
                else:
                    # Already a Pitcher; merge or replace pitching stats via setters
                    if mode == 'merge':
                        # Ensure message pipe exists
                        try:
                            if getattr(existing_player, 'message', None) is None:
                                if hasattr(parent, 'message') and getattr(parent, 'message', None) is not None:
                                    existing_player.message = parent.message
                                else:
                                    class _Msg:
                                        def show_message(self, m):
                                            print(f"[MESSAGE] {m}")
                                    existing_player.message = _Msg()
                        except Exception:
                            pass
                        # Normalize existing pitcher's numeric fields to integers
                        _normalize_numeric_attrs(existing_player, [
                            'wins','losses','games_played','games_started','games_completed','shutouts','saves','save_ops','ip','p_at_bats','p_hits','p_runs','er','p_hr','p_hb','p_bb','p_so'
                        ])
                        pitcher_setters = [
                            ('games_played','set_games_played'), ('wins','set_wins'), ('losses','set_losses'),
                            ('games_started','set_games_started'), ('games_completed','set_games_completed'),
                            ('shutouts','set_shutouts'), ('saves','set_saves'), ('save_ops','set_save_ops'),
                            ('p_at_bats','set_p_at_bats'),
                            ('p_hits','set_p_hits'), ('p_bb','set_p_bb'), ('p_so','set_p_so'), ('p_hr','set_p_hr'), ('p_hb','set_p_hb'), ('p_runs','set_p_runs'), ('er','set_er'),
                            ('ip','set_ip')
                        ]
                        for attr_name, setter_name in pitcher_setters:
                            try:
                                delta = _to_int(getattr(pitcher, attr_name, 0))
                                if delta:
                                    setter = getattr(existing_player, setter_name, None)
                                    if callable(setter):
                                        setter(delta)
                                    else:
                                        setattr(existing_player, attr_name, _to_int(getattr(existing_player, attr_name, 0)) + delta)
                            except Exception as e:
                                try:
                                    print(f"[MERGE][PITCHER] Failed {attr_name}: delta={delta} name={getattr(existing_player,'name',None)} id={getattr(existing_player,'playerID',None)} team={getattr(find_team,'name',None)} ip={getattr(existing_player,'ip',None)} p_ab={getattr(existing_player,'p_at_bats',None)} error={e}")
                                except Exception:
                                    pass
                                try:
                                    if hasattr(parent, 'message') and getattr(parent, 'message', None) is not None:
                                        parent.message.show_message(f"Merge warning for {getattr(existing_player,'name','pitcher')}: could not merge {attr_name}.", btns_flag=False, timeout_ms=2000)
                                except Exception:
                                    pass
                    else:
                        for k in ['wins','losses','games_played','games_started','games_completed','shutouts','saves','save_ops','ip','p_at_bats','p_hits','p_runs','er','p_hr','p_hb','p_bb','p_so','WHIP','p_avg','k_9','bb_9']:
                            setattr(existing_player, k, getattr(pitcher, k, getattr(existing_player, k, 0)))
                    # recalc derived pitching
                    try:
                        if hasattr(existing_player, 'set_era'): existing_player.set_era()
                        if hasattr(existing_player, 'set_WHIP'): existing_player.set_WHIP()
                        if hasattr(existing_player, 'set_p_avg'): existing_player.set_p_avg()
                        if hasattr(existing_player, 'set_k_9'): existing_player.set_k_9()
                        if hasattr(existing_player, 'set_bb_9'): existing_player.set_bb_9()
                    except Exception:
                        pass
            else:
                # No existing player, attach pitcher
                pitcher.team = find_team
                pitcher.teamID = find_team.teamID
                pitcher.league = league
                pitcher.leagueID = league.leagueID
                try:
                    if 'pitcher' not in pitcher.positions:
                        pitcher.positions.append('pitcher')
                except Exception:
                    pass
                # avoid duplicate by name+playerID
                dup = False
                for existing in find_team.players:
                    if getattr(existing, 'playerID', None) == getattr(pitcher, 'playerID', None):
                        dup = True
                        break
                    if existing.name == pitcher.name and 'pitcher' in getattr(existing, 'positions', []):
                        dup = True
                        break
                if not dup:
                    find_team.add_player(pitcher)
        else:
            print(f"Warning: team not found for pitcher {getattr(pitcher, 'name', '')} (teamID/team name mismatch)")

    # assign Main Window - league - inherited by all - with CSV load
    setattr(parent, 'league', league)
    
    # Update league references in all child views to ensure they use the new league object
    if parent:
        try:
            if hasattr(parent, 'league_view_players'):
                parent.league_view_players.league = league
                print("Updated league_view_players league reference")
            if hasattr(parent, 'league_view_teams'):
                parent.league_view_teams.league = league
                print("Updated league_view_teams league reference")
            if hasattr(parent, 'leaderboard'):
                parent.leaderboard.league = league
                print("Updated leaderboard league reference")
            if hasattr(parent, 'refresh'):
                parent.refresh.league = league
                print("Updated refresh league reference")
        except Exception as e:
            print(f"Warning: Could not update all league references: {e}")

    # Recompute team-level derived stats after merges
    try:
        for t in league.get_all_objs():
            if hasattr(t, 'set_wl_avg'):
                t.set_wl_avg()
            if hasattr(t, 'set_bat_avg'):
                t.set_bat_avg()
            if hasattr(t, 'set_team_era'):
                t.set_team_era()
    except Exception as e:
        print(f"Warning recomputing team derived stats: {e}")

    # call refresh tree widget views after Main Window league updated
    try:
        if hasattr(parent, 'refresh_view') and callable(parent.refresh_view):
            parent.refresh_view()
    except Exception as e:
        print(f"Refresh note: {e}")
        
def load_league_gui(attr, val, league):
    """Set league attribute during GUI/in-memory build."""
    setattr(league, attr, val)

def load_team_gui(attr, val, team):
    """Set team attribute during GUI/in-memory build."""
    setattr(team, attr, val)

def load_player_gui(attr, val, player):
    """Set player attribute during GUI/in-memory build."""
    setattr(player, attr, val) 

def load_pitcher_gui(attr, val, pitcher):
    """Set pitcher attribute during GUI/in-memory build."""
    setattr(pitcher, attr, val)

# ----------------------- Persistence Helpers -----------------------
def persist_derived_stats_to_db(db_path: str, league: LinkedList):
    """Write recalculated player/pitcher derived stats back to DB to keep storage consistent."""
    """Write recalculated derived stats back to the database for consistency."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        for team in league.get_all_objs():
            try:
                roster = getattr(team, 'players', [])
            except Exception:
                roster = []
            for p in roster:
                pid = getattr(p, 'playerID', None)
                if pid is None:
                    continue
                # Update player derived offense
                try:
                    obp = float(getattr(p, 'OBP', 0) or 0)
                    babip = float(getattr(p, 'BABIP', 0) or 0)
                    slg = float(getattr(p, 'SLG', 0) or 0)
                    avg = float(getattr(p, 'AVG', 0) or 0)
                    iso = float(getattr(p, 'ISO', 0) or 0)
                    cur.execute(
                        "UPDATE player SET OBP=?, BABIP=?, SLG=?, AVG=?, ISO=? WHERE playerID=?",
                        (obp, babip, slg, avg, iso, pid)
                    )
                except Exception as e:
                    print(f"Persist player derived failed (playerID={pid}): {e}")

                # Update pitcher derived if pitcher row exists
                try:
                    era = float(getattr(p, 'era', 0) or 0)
                    whip = float(getattr(p, 'WHIP', 0) or 0)
                    p_avg = float(getattr(p, 'p_avg', 0) or 0)
                    k_9 = float(getattr(p, 'k_9', 0) or 0)
                    bb_9 = float(getattr(p, 'bb_9', 0) or 0)
                    cur.execute(
                        "UPDATE pitcher SET era=?, WHIP=?, p_avg=?, k_9=?, bb_9=? WHERE playerID=?",
                        (era, whip, p_avg, k_9, bb_9, pid)
                    )
                except Exception as e:
                    print(f"Persist pitcher derived failed (playerID={pid}): {e}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Persist derived stats DB error: {e}")

# ----------------------- Full CSV Loader -----------------------
def load_all_csv_to_db(league, directory: str, db_path: str, stack, parent=None):
    """End-to-end CSV import: session select → DB choice/strategy → import → build → summary."""
    """
    Full workflow: session selection + database choice + overwrite choice + import + summary.
    """
    
    # Removed extra prompt; behavior is decided by database choice dialog
    
    csv_files = get_csv_files(directory)
    sessions = group_csv_by_session(csv_files)

    if not sessions:
        print("⚠️ No valid CSV session files found in directory.")
        return

    # Step 1: Session choice
    if len(sessions) > 1:
        session_dialog = SessionChoiceDialog(sessions, parent=parent)
        session_dialog.exec()
        chosen_session = session_dialog.choice
        if not chosen_session:
            print("⏹️ CSV import cancelled: no session selected")
            return
    else:
        chosen_session = list(sessions.keys())[0]

    selected_files = sessions[chosen_session]

    # Step 2: Database choice
    db_dialog = DatabaseChoiceDialog(parent=parent)
    db_dialog.exec()
    db_choice = db_dialog.choice
    if not db_choice:
        print("⏹️ CSV import cancelled: no database choice")
        return

    if db_choice == "new database":
        print("Creating new database...")
        # Step 2a: Close any existing connections to the database
        try: 
            conn = sqlite3.connect(db_path)
            conn.close() 
        except Exception as e: 
            print(f"Warning: Could not connect to close existing connection: {e}")
        
        # Step 2b: Delete the existing database file to drop all data
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"Database file '{db_path}' deleted successfully.")
            except OSError as e:
                print(f"Error: Failed to delete database file '{db_path}': {e}")
                print("Cannot create new database without deleting the old one. Aborting.")
                return
        
        # Step 2c: Clear the league object in memory to remove all existing data
        print("Clearing league data from memory...")
        # Clear all teams from league
        league.teams = []
        
        print(f"League data cleared. Team count: {len(league.teams)}")
        print("Only CSV data will be loaded.")
        
        # Clear all GUI tree widgets to remove visual display of old data
        if parent and hasattr(parent, 'league_view_players'):
            print("Clearing GUI tree widgets...")
            try:
                # Clear player views
                if hasattr(parent.league_view_players, 'tree1_top'):
                    parent.league_view_players.tree1_top.clear()
                if hasattr(parent.league_view_players, 'tree2_top'):
                    parent.league_view_players.tree2_top.clear()
                
                # Clear team views
                if hasattr(parent, 'league_view_teams'):
                    if hasattr(parent.league_view_teams, 'tree1_bottom'):
                        parent.league_view_teams.tree1_bottom.clear()
                    if hasattr(parent.league_view_teams, 'tree2_bottom'):
                        parent.league_view_teams.tree2_bottom.clear()
                
                # Clear leaderboard
                if hasattr(parent, 'leaderboard') and hasattr(parent.leaderboard, 'tree_widget'):
                    parent.leaderboard.tree_widget.clear()
                    # Clear internal leaderboard data structure to prevent stale data
                    if hasattr(parent.leaderboard, 'leaderboard_list'):
                        parent.leaderboard.leaderboard_list.clear()
                    
                print("GUI cleared successfully.")
            except Exception as e:
                print(f"Warning: Could not clear all GUI elements: {e}")
        
        print("League data cleared. Only CSV data will be loaded.")
        
        # Step 2d: Create fresh database with empty tables
        try:
            init_new_db(db_path, league)
            print("New database initialized with empty tables.")
        except Exception as e:
            print(f"Error: Failed to initialize new database: {e}")
            return

        mode = "overwrite"  # New DB is empty, so all inserts will be new
    else:
        # Step 3: Replace (drop and reload) or Merge (additive updates)
        strategy_dialog = ReplaceMergeDialog(parent=parent)
        strategy_dialog.exec()
        strategy = strategy_dialog.choice
        if strategy == "cancel":
            print("⏹️ CSV import cancelled by user")
            return
        if strategy == "replace":
            # Remove DB file to drop all tables/data
            try:
                if os.path.exists(db_path):
                    try:
                        ctmp = sqlite3.connect(db_path)
                        ctmp.close()
                    except Exception:
                        pass
                    os.remove(db_path)
            except Exception as e:
                print(f"Error removing DB file on replace: {e}")
                return
            # Clear in-memory league and GUI
            try:
                league.teams = []
                if parent and hasattr(parent, 'league_view_players'):
                    if hasattr(parent.league_view_players, 'tree1_top'):
                        parent.league_view_players.tree1_top.clear()
                    if hasattr(parent.league_view_players, 'tree2_top'):
                        parent.league_view_players.tree2_top.clear()
                if parent and hasattr(parent, 'league_view_teams'):
                    if hasattr(parent.league_view_teams, 'tree1_bottom'):
                        parent.league_view_teams.tree1_bottom.clear()
                    if hasattr(parent.league_view_teams, 'tree2_bottom'):
                        parent.league_view_teams.tree2_bottom.clear()
                if parent and hasattr(parent, 'leaderboard') and hasattr(parent.leaderboard, 'tree_widget'):
                    parent.leaderboard.tree_widget.clear()
                    # Clear internal leaderboard data structure to prevent stale data
                    if hasattr(parent.leaderboard, 'leaderboard_list'):
                        parent.leaderboard.leaderboard_list.clear()
            except Exception as e:
                print(f"Warning clearing in-memory/GUI on replace: {e}")
            # Recreate schema
            try:
                init_new_db(db_path, league)
            except Exception as e:
                print(f"Error initializing DB on replace: {e}")
                return
            mode = "overwrite"
        elif strategy == "merge":
            mode = "merge"

    # Step 4: Insert CSVs (collect to local instance stack regardless of caller)
    conn = sqlite3.connect(db_path)
    summary = {}
    local_stack = InstanceStack()
    try:
        for table, filepath in selected_files:
            insert_csv_to_table(table, filepath, conn, mode, summary, local_stack, parent, league)
    finally:
        conn.close()

    # Step 4b: After all tables processed, build GUI once
    try:
        instances = local_stack.getInstances()
        if instances:
            load_all_gui(instances, parent, league, mode)
            # After in-memory recompute, persist derived stats to DB for consistency
            try:
                persist_derived_stats_to_db(db_path, league)
            except Exception as e:
                print(f"Note: derived stats persistence failed: {e}")
    except Exception as e:
        import traceback
        print(f"Build GUI after CSV import failed: {e}")
        print(f"Full traceback:\n{traceback.format_exc()}")

    # Step 5: Show summary
    summary_dialog = SummaryDialog(summary, parent=parent)
    summary_dialog.exec()



if __name__ == "__main__":
   from src.utils.path_resolver import get_data_path, get_database_path
   app = QApplication(sys.argv)
   csv_path = str(get_data_path("exports"))
   db_path = str(get_database_path())
   load_all_csv_to_db("data/exports", db_path)  # Using path resolver for db_path
   

   sys.exit(app.exec())
