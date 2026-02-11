"""
Ensure the NL (local SQL) database has the expected schema when running frozen.
Used after clear_database_on_startup so local Execute SQL has league/team/player/pitcher tables.
"""
import sqlite3
import sys
from pathlib import Path


def _minimal_league():
    """Minimal league-like object for init_new_db when ensuring schema only."""
    class _League:
        leagueID = 1
        admin = {
            "Name": "Default League",
            "Commissioner": "",
            "Treasurer": "",
            "Communications": "",
            "Historian": "",
            "Recruitment": "",
            "Start": "",
            "Stop": "",
        }
    return _League()


def _schema_exists(db_path: Path) -> bool:
    """Return True if the DB has the expected 'team' table (and thus usable schema)."""
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='team' LIMIT 1"
        )
        exists = cur.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


def ensure_nl_database_schema():
    """
    When running frozen, ensure the database at get_database_path() has the
    league/team/player/pitcher schema. Idempotent: only runs init if the
    team table is missing (e.g. first run or after clear_database_on_startup).
    """
    if not getattr(sys, "frozen", False):
        return
    from src.utils.path_resolver import get_database_path
    from src.data.save.save_manager import init_new_db

    db_path = get_database_path()
    if _schema_exists(db_path):
        return
    try:
        init_new_db(str(db_path), _minimal_league())
    except Exception as e:
        # Log but do not crash startup
        print(f"[ensure_nl_db] Failed to ensure NL database schema: {e}")
