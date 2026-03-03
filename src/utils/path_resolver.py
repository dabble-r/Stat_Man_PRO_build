"""
Path resolution utilities for development and PyInstaller bundled modes.
Ensures paths work correctly whether running from source or as a bundled executable.
"""
import os
import sys
from pathlib import Path


def get_app_base_path():
    """
    Get the base path where the application is running from.
    For bundled executables, this is the directory containing the .exe.
    For development, this is the project root.
    server_fail_12 P2/P3: When frozen on Windows, if exe dir is not writable,
    fall back to %LOCALAPPDATA%/stat_man_g so data/logs can be created.

    When the process is a server subprocess started by the frozen app, the parent
    sets STATMANG_APP_BASE so the server uses the same data directory as the main app.

    Returns:
        str: Absolute path to application base directory
    """
    env_base = os.environ.get("STATMANG_APP_BASE", "").strip()
    if env_base:
        return env_base
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        if sys.platform.startswith("win"):
            # P2/P3: try exe dir first; if not writable, use LOCALAPPDATA
            try:
                test_dir = os.path.join(exe_dir, "data", "logs")
                os.makedirs(test_dir, exist_ok=True)
                return exe_dir
            except (OSError, PermissionError):
                localappdata = os.environ.get("LOCALAPPDATA", "")
                if localappdata:
                    fallback = os.path.join(localappdata, "stat_man_g")
                    try:
                        os.makedirs(os.path.join(fallback, "data", "logs"), exist_ok=True)
                        return fallback
                    except (OSError, PermissionError):
                        pass
        return exe_dir
    else:
        # Running in development mode
        return os.path.abspath(".")


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for development and PyInstaller bundle.
    Resources bundled with PyInstaller are extracted to a temp folder (_MEIPASS).
    
    Args:
        relative_path: Path relative to application root
        
    Returns:
        str: Absolute path that works in both dev and bundled mode
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in development mode
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def get_data_path(*relative_paths):
    """
    Get absolute path to a data file/directory.
    Data files are stored next to the executable in bundled mode.
    
    Args:
        *relative_paths: Path components relative to data/ directory
                       e.g., ('database', 'League.db') -> data/database/League.db
        
    Returns:
        Path: Path object pointing to the data location
    """
    app_base = get_app_base_path()
    data_path = Path(app_base) / "data" / Path(*relative_paths)
    # Ensure parent directories exist
    data_path.parent.mkdir(parents=True, exist_ok=True)
    return data_path


def get_database_path():
    """
    Get the path to the League database.

    When the process is a server subprocess started by the frozen app, the parent
    sets STATMANG_DB_PATH so the server uses the same database as the main app.
    
    Returns:
        Path: Path to data/database/League.db
    """
    env_db = os.environ.get("STATMANG_DB_PATH", "").strip()
    if env_db:
        return Path(env_db)
    return get_data_path("database", "League.db")


def get_server_tests_log_path():
    """
    Return path to server test findings log: data/logs/server_tests.log under app base.
    Ensures data/logs exists (creates parent directories). Use for all server test
    log output so Windows and frozen builds write to the same file.
    
    Returns:
        Path: Path to data/logs/server_tests.log
    """
    return get_data_path("logs", "server_tests.log")


