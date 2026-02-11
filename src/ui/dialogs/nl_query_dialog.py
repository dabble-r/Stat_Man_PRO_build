"""
NL-to-SQL Query Dialog for natural language database queries.

Provides a GUI for natural language database queries using OpenAI and FastAPI.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QMessageBox, QHeaderView, QSplitter, QTableView,
    QComboBox, QAbstractItemView, QFileDialog
)
from PySide6.QtCore import QThread, Signal, Qt, QAbstractTableModel, QTimer
from PySide6.QtGui import QCloseEvent, QAction, QPixmap, QPainter, QColor, QFontMetrics
from PySide6.QtWidgets import QLabel
from src.utils.nl_sql_server import NLServerManager
from src.utils.nl_query_cache import NLQueryCache
from src.utils.path_resolver import get_data_path
from src.utils.api_key_manager import APIKeyManager
from src.utils.global_server_manager import GlobalServerManager
from src.visualization.viz_plot_builder import build_figure
from src.ui.dialogs.viz_options_dialog import VizOptionsDialog
from src.ui.dialogs.viz_viewer_dialog import VizViewerDialog
from typing import Optional, Tuple
import os
import requests
import logging
import pandas as pd
import csv
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PandasTableModel(QAbstractTableModel):
    """Table model for displaying pandas DataFrame in QTableView."""
    
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe.copy()
    
    def rowCount(self, parent=None):
        return len(self._dataframe)
    
    def columnCount(self, parent=None):
        return len(self._dataframe.columns)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        if role == Qt.DisplayRole:
            value = self._dataframe.iloc[index.row(), index.column()]
            # Handle NaN values
            if pd.isna(value):
                return ""
            return str(value)
        
        if role == Qt.TextAlignmentRole:
            # Align numbers to right, text to left
            value = self._dataframe.iloc[index.row(), index.column()]
            if isinstance(value, (int, float)) and not pd.isna(value):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._dataframe.columns[section])
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(self._dataframe.index[section] + 1)  # 1-indexed row numbers
        return None
    
    def get_dataframe(self):
        """Get the underlying DataFrame."""
        return self._dataframe


class NLQueryThread(QThread):
    """Thread for sending NL query to FastAPI server - only gets SQL, doesn't execute."""
    
    finished = Signal(str)  # Emits SQL query string or None
    
    def __init__(self, api_key: str, query: str, fastapi_url: str):
        super().__init__()
        self.api_key = api_key
        self.query = query
        self.fastapi_url = fastapi_url
    
    def run(self):
        """Send NL query and get SQL only (does not execute)."""
        try:
            # Use /nl_to_sql endpoint which only generates SQL, doesn't execute
            response = requests.post(
                f"{self.fastapi_url}/nl_to_sql",
                json={"question": self.query},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=(10, 120)
            )
            
            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error") if response.headers.get("content-type", "").startswith("application/json") else response.text
                logger.error(f"Query failed with status {response.status_code}: {error_detail}")
                self.finished.emit(None)
                return
            
            # Get SQL from JSON response
            result = response.json()
            sql_query = result.get("sql", "").strip()
            
            if not sql_query:
                logger.error("No SQL query in response")
                self.finished.emit(None)
                return
            
            self.finished.emit(sql_query)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}", exc_info=True)
            self.finished.emit(None)
        except Exception as e:
            logger.error(f"Query thread error: {str(e)}", exc_info=True)
            self.finished.emit(None)


class SQLExecuteThread(QThread):
    """Thread for executing SQL query on database via MCP server."""
    
    finished = Signal(list)  # Emits list of result dicts or None
    
    def __init__(self, sql: str, mcp_url: str):
        super().__init__()
        self.sql = sql
        self.mcp_url = mcp_url
    
    def run(self):
        """Execute SQL query via MCP server."""
        try:
            response = requests.post(
                f"{self.mcp_url}/execute",
                json={"sql": self.sql},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"SQL execution failed with status {response.status_code}: {response.text}")
                self.finished.emit(None)
                return
            
            result_data = response.json()
            results = result_data.get("results", [])
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"SQL execution error: {str(e)}", exc_info=True)
            self.finished.emit(None)


def _query_db_log_path():
    """Path for SQL execution log: data/logs/query_db.log (under app base)."""
    from pathlib import Path
    from src.utils.path_resolver import get_app_base_path
    base = Path(get_app_base_path())
    log_dir = base / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "query_db.log"


def _get_db_state(conn) -> str:
    """Return a short description of DB state (table names and row counts) for logging."""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = [row[0] for row in cur.fetchall()]
    lines = []
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM [{t}]")
            n = cur.fetchone()[0]
            lines.append(f"  {t}: {n} rows")
        except Exception:
            lines.append(f"  {t}: (count error)")
    return "\n".join(lines) if lines else "  (no user tables)"


class LocalSQLExecuteThread(QThread):
    """Thread for executing SQL query locally on SQLite database (no server required)."""

    finished = Signal(object)  # Emits list of result dicts or None on success (Shiboken-safe)
    
    def __init__(self, sql: str):
        super().__init__()
        self.sql = sql
    
    def run(self):
        """Execute SQL query directly on SQLite database."""
        try:
            import sqlite3
            from src.utils.path_resolver import get_database_path
            from datetime import datetime

            db_path = get_database_path()
            logger.info(f"[LocalSQLExecute] Executing query locally on {db_path}")
            
            # Connect to database
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
            
            try:
                # DB state for logging (before query)
                db_state = _get_db_state(conn)

                cursor = conn.cursor()
                cursor.execute(self.sql)
                
                # Fetch all results
                rows = cursor.fetchall()
                
                # Convert to list of dicts
                results = []
                for row in rows:
                    results.append(dict(row))
                
                logger.info(f"[LocalSQLExecute] Query executed successfully, returned {len(results)} rows")
                self.finished.emit(results)

                # Log to tests/logs/query_db.log (no behavior change)
                try:
                    log_path = _query_db_log_path()
                    max_rows_log = 100
                    if len(results) > max_rows_log:
                        results_repr = f"{results[:max_rows_log]} ... ({len(results) - max_rows_log} more rows)"
                    else:
                        results_repr = str(results)
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n{'='*60}\n")
                        f.write(f"[{datetime.now().isoformat()}] Execute SQL\n")
                        f.write(f"db_path: {db_path}\n")
                        f.write(f"query:\n{self.sql}\n")
                        f.write(f"db_state (before query):\n{db_state}\n")
                        f.write(f"results: {results_repr}\n")
                except Exception as log_err:
                    logger.debug(f"[LocalSQLExecute] Could not write query_db.log: {log_err}")
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"[LocalSQLExecute] SQL execution error: {str(e)}", exc_info=True)
            self.finished.emit(None)
            # Log failure to query_db.log
            try:
                from datetime import datetime
                from src.utils.path_resolver import get_database_path
                log_path = _query_db_log_path()
                db_state = ""
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(get_database_path()))
                    db_state = _get_db_state(conn)
                    conn.close()
                except Exception:
                    db_state = "(could not get state)"
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"[{datetime.now().isoformat()}] Execute SQL (FAILED)\n")
                    f.write(f"db_path: {get_database_path()}\n")
                    f.write(f"query:\n{self.sql}\n")
                    f.write(f"db_state:\n{db_state}\n")
                    f.write(f"error: {e}\n")
            except Exception as log_err:
                logger.debug(f"[LocalSQLExecute] Could not write query_db.log: {log_err}")


class NLQueryDialog(QDialog):
    """Dialog for NL-to-SQL queries."""
    
    # Signal emitted when query completes successfully
    query_completed = Signal(dict)  # {'sql': str, 'results': list}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NL-to-SQL Query")
        self.setMinimumSize(1250, 750)
        
        # Make dialog stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        # State
        self.api_key: Optional[str] = None
        self.server_manager: Optional[NLServerManager] = None
        self.query_thread: Optional[NLQueryThread] = None
        self.execute_thread: Optional[SQLExecuteThread] = None
        self.local_execute_thread: Optional[LocalSQLExecuteThread] = None
        self.current_sql: Optional[str] = None
        self.query_results: Optional[list] = None  # Keep for backward compatibility
        self.query_results_df: Optional[pd.DataFrame] = None  # DataFrame storage
        self._original_dataframe: Optional[pd.DataFrame] = None  # Store original for filter reset
        self._is_closing = False  # Flag to prevent error messages during close
        self._is_cached_query = False  # Track if current query is from cache (for local execution)
        
        # Server failure state (stored, not shown immediately)
        self._fastapi_failure_msg: Optional[str] = None
        self._mcp_failure_msg: Optional[str] = None
        self._servers_starting = False  # Track if servers are in startup phase
        self._servers_ready_message_shown = False  # Show "Servers Ready" only once per start
        # Issue 4: optional periodic check while starting (catch missed ready signal)
        self._servers_starting_poll_timer: Optional[QTimer] = None
        self._servers_starting_poll_stop_timer: Optional[QTimer] = None
        
        # API Key Manager and Global Server Manager
        self.api_key_manager = APIKeyManager()
        self.global_server_manager = GlobalServerManager.get_instance(parent=self)
        
        # Connect to global server manager signals
        self.global_server_manager.servers_ready.connect(self._on_servers_ready)
        self.global_server_manager.fastapi_status_changed.connect(
            lambda status: self._update_server_status_icon(status and self.global_server_manager.is_servers_running())
        )
        self.global_server_manager.mcp_status_changed.connect(
            lambda status: self._update_server_status_icon(status and self.global_server_manager.is_servers_running())
        )
        
        # Initialize query cache (with error handling to prevent blocking server startup)
        try:
            self.query_cache = NLQueryCache(max_size=50, persist=True)
        except Exception as e:
            logger.warning(f"Failed to initialize query cache: {e}", exc_info=True)
            # Create cache without persistence as fallback - don't block server startup
            try:
                self.query_cache = NLQueryCache(max_size=50, persist=False)
            except Exception as e2:
                logger.error(f"Failed to initialize cache even without persistence: {e2}", exc_info=True)
                # If all else fails, create a minimal cache that won't persist
                self.query_cache = None  # Will be checked before use
        
        # Create UI
        self._create_ui()
        self._setup_initial_state()
    
    def _create_ui(self):
        """Create the UI layout with toolbar, left panel (inputs) and right panel (SQL + results)."""
        main_layout = QVBoxLayout()  # Changed to QVBoxLayout for toolbar
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Toolbar removed; cache count is in right panel above Clear Cache
        
        # Content area with left and right panels
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left panel (inputs)
        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel, stretch=1)
        
        # Right panel (SQL display + results)
        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)
        
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with API key and NL query inputs."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # API Key Section
        api_key_label_layout = QHBoxLayout()
        self.api_key_help_btn = QPushButton("?")
        self.api_key_help_btn.setFixedSize(22, 22)
        self.api_key_help_btn.setToolTip("How to get an API key")
        self.api_key_help_btn.clicked.connect(self._show_api_key_help)
        api_key_label_layout.addWidget(self.api_key_help_btn)
        api_key_label = QLabel("OpenAI API Key:")
        self.server_status_icon = QLabel()
        self.server_status_icon.setFixedSize(16, 16)
        self.server_status_icon.setToolTip("Server status: Red = Stopped, Green = Running")
        self._update_server_status_icon(False)  # Initial state: stopped
        api_key_label_layout.addWidget(api_key_label)
        api_key_label_layout.addWidget(self.server_status_icon)
        api_key_label_layout.addStretch()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key...")
        self.api_key_input.textChanged.connect(self._on_api_key_input_changed)
        
        # API Key buttons layout
        api_key_buttons_layout = QHBoxLayout()
        self.submit_api_key_btn = QPushButton("Submit API Key")
        self.submit_api_key_btn.clicked.connect(self._handle_api_key_submit)
        api_key_buttons_layout.addWidget(self.submit_api_key_btn)
        
        self.stop_servers_btn = QPushButton("Stop Servers")
        self.stop_servers_btn.clicked.connect(self._handle_stop_servers)
        self.stop_servers_btn.setEnabled(False)  # Disabled until servers are running
        self.stop_servers_btn.setToolTip("Stop both FastAPI and MCP servers")
        api_key_buttons_layout.addWidget(self.stop_servers_btn)
        
        self.restart_servers_btn = QPushButton("Restart Servers")
        self.restart_servers_btn.clicked.connect(self._handle_restart_servers)
        self.restart_servers_btn.setEnabled(False)  # Disabled until API key is submitted
        self.restart_servers_btn.setToolTip("Restart servers using the current API key")
        api_key_buttons_layout.addWidget(self.restart_servers_btn)
        
        layout.addLayout(api_key_label_layout)
        layout.addWidget(self.api_key_input)
        layout.addLayout(api_key_buttons_layout)
        
        # Separator
        separator = QLabel("─" * 40)
        separator.setAlignment(Qt.AlignCenter)
        layout.addWidget(separator)
        
        # NL Query Section
        nl_query_label = QLabel("Natural Language Query:")
        self.nl_query_input = QTextEdit()
        self.nl_query_input.setPlaceholderText("Enter your natural language query...\nExample: Show me all players with batting average above 0.300")
        self.nl_query_input.setMinimumHeight(150)
        
        self.submit_nl_query_btn = QPushButton("Submit NL Query")
        self.submit_nl_query_btn.clicked.connect(self._handle_nl_query_submit)
        
        layout.addWidget(nl_query_label)
        layout.addWidget(self.nl_query_input)
        layout.addWidget(self.submit_nl_query_btn)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Create right panel with cached queries, SQL display, execute button, and results."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Cached Queries Section (top of right panel, above SQL display)
        # NOTE: This section is ALWAYS enabled, no API key required
        # Cache count at top right, above Clear Cache button
        cache_count_layout = QHBoxLayout()
        cache_count_layout.addStretch()
        self.cache_size_label = QLabel("Cache: 0/50")
        cache_count_layout.addWidget(self.cache_size_label)
        layout.addLayout(cache_count_layout)
        
        cached_label = QLabel("Load Cached Query:")
        self.query_cache_combo = QComboBox()
        self.query_cache_combo.setEditable(False)
        self.query_cache_combo.setPlaceholderText("Select a cached query...")
        # Use activated signal for user selections (fires when user clicks an item)
        # This signal only fires on actual user interaction, not programmatic changes
        self.query_cache_combo.activated.connect(self._on_cached_query_selected)
        # Cache dropdown is always enabled (independent of API key state)
        
        # Clear cache button
        self.clear_cache_btn = QPushButton("Clear Cache")
        self.clear_cache_btn.clicked.connect(self._handle_clear_cache)
        self.clear_cache_btn.setEnabled(False)  # Disabled when cache is empty
        
        # Layout for cache controls
        cache_buttons_layout = QHBoxLayout()
        cache_buttons_layout.addWidget(cached_label)
        cache_buttons_layout.addWidget(self.query_cache_combo, stretch=1)
        cache_buttons_layout.addWidget(self.clear_cache_btn)
        
        layout.addLayout(cache_buttons_layout)
        
        # Separator (optional, for visual separation)
        separator1 = QLabel("─" * 40)
        separator1.setAlignment(Qt.AlignCenter)
        layout.addWidget(separator1)
        
        # SQL Display Section (below cached queries)
        sql_label = QLabel("Generated SQL Query:")
        self.sql_display = QTextEdit()
        self.sql_display.setReadOnly(False)
        self.sql_display.setPlaceholderText("SQL query will appear here after submitting NL query...")
        self.sql_display.setMinimumHeight(200)
        
        # Import/Export buttons (uniform style with other buttons)
        import_export_layout = QHBoxLayout()
        import_export_layout.setSpacing(10)
        
        self.import_queries_btn = QPushButton("Import Queries from CSV")
        self.import_queries_btn.setToolTip("Import formatted SQL queries from CSV file (from formatted/ folder)")
        self.import_queries_btn.clicked.connect(self._handle_import_queries_csv)
        
        self.export_query_results_btn = QPushButton("Export Query and Results")
        self.export_query_results_btn.setToolTip("Export formatted SQL query and results to separate folders")
        self.export_query_results_btn.clicked.connect(self._handle_export_query_results)
        
        self.visualize_btn = QPushButton("Visualize")
        self.visualize_btn.setToolTip("Create a chart from query results (bar, line, scatter, histogram, box)")
        self.visualize_btn.clicked.connect(self._handle_visualize)
        self.visualize_btn.setEnabled(False)
        
        import_export_layout.addWidget(self.import_queries_btn)
        import_export_layout.addWidget(self.export_query_results_btn)
        import_export_layout.addWidget(self.visualize_btn)
        import_export_layout.addStretch()
        
        self.execute_sql_btn = QPushButton("Execute SQL Query")
        self.execute_sql_btn.clicked.connect(self._handle_execute_sql)
        
        layout.addWidget(sql_label)
        layout.addWidget(self.sql_display)
        layout.addLayout(import_export_layout)
        layout.addWidget(self.execute_sql_btn)
        
        # Separator
        separator = QLabel("─" * 40)
        separator.setAlignment(Qt.AlignCenter)
        layout.addWidget(separator)
        
        # Results Section (bottom right)
        results_label = QLabel("Query Results:")
        self.results_table = QTableView()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.results_table.setSortingEnabled(True)  # Enable sorting
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setMinimumHeight(250)
        
        # Status label
        self.results_status_label = QLabel("Results will appear here after executing SQL query...")
        self.results_status_label.setAlignment(Qt.AlignCenter)
        self.results_status_label.setStyleSheet("color: gray; font-style: italic;")
        
        layout.addWidget(results_label)
        layout.addWidget(self.results_status_label)
        layout.addWidget(self.results_table)
        
        panel.setLayout(layout)
        return panel
    
    def _setup_initial_state(self):
        """Set initial widget states."""
        # Try to load saved API key
        saved_api_key = self.api_key_manager.load_api_key()
        if saved_api_key:
            self.api_key = saved_api_key
            self.api_key_input.setText(saved_api_key)  # Show in input (will be masked)
            logger.info("Loaded saved API key from encrypted storage")
        
        # Check if servers are already running via GlobalServerManager
        # Note: With new logic, servers should not persist, so this check is mainly for safety
        if self.global_server_manager.is_servers_running():
            logger.info("Servers are already running, connecting to existing instance")
            self.server_manager = self.global_server_manager.get_server_manager()
            self._connect_server_signals()
            self._on_servers_ready()
        elif saved_api_key:
            # Servers not running but API key exists - user can restart servers easily
            logger.info("API key found but servers not running - user can restart servers")
            # Pre-fill API key input for easy restart (will be masked)
            self.api_key_input.setText(saved_api_key)
        
        # API key dependent widgets
        self.nl_query_input.setEnabled(False)
        self.submit_nl_query_btn.setEnabled(False)
        self.sql_display.setEnabled(False)
        self.execute_sql_btn.setEnabled(False)  # For newly generated queries
        self.results_table.setEnabled(False)
        
        # Update status icon based on server state
        self._update_server_status_icon(self.global_server_manager.is_servers_running())
        
        # Cache dropdown is ALWAYS enabled (no API key required)
        # Defer cache dropdown refresh to avoid blocking initialization
        if self.query_cache is not None:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self._refresh_cache_dropdown)
        # Note: query_cache_combo is enabled by default, no need to disable it
    
    def _update_server_status_icon(self, is_running: bool):
        """Update server status icon (red/green)."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle: green if running, red if stopped
        color = QColor(0, 255, 0) if is_running else QColor(255, 0, 0)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        self.server_status_icon.setPixmap(pixmap)
        status_text = "Running" if is_running else "Stopped"
        self.server_status_icon.setToolTip(f"Server status: {status_text}")
    
    def _connect_server_signals(self):
        """Connect to server manager signals."""
        if not self.server_manager:
            return
        
        self.server_manager.all_servers_ready.connect(self._on_servers_ready)
        self.server_manager.fastapi_ready.connect(self._on_fastapi_ready)
        self.server_manager.mcp_ready.connect(self._on_mcp_ready)
        self.server_manager.fastapi_failed.connect(self._on_fastapi_failed)
        self.server_manager.mcp_failed.connect(self._on_mcp_failed)
    
    def _show_api_key_help(self):
        """Show help dialog for obtaining an OpenAI API key. Bullets on separate lines, OpenAI link clickable."""
        url = "https://platform.openai.com"
        lines = [
            "Create an account at " + url + ".",
            "Open Dashboard → API Keys → Create new key.",
            "Copy and store it securely.",
        ]
        help_html = (
            "<ul style='margin: 0; padding-left: 20px;'>"
            "<li>Create an account at <a href=\"" + url + "\">" + url + "</a>.</li>"
            "<li>Open Dashboard → API Keys → Create new key.</li>"
            "<li>Copy and store it securely.</li>"
            "</ul>"
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("OpenAI API Key")
        fm = QFontMetrics(dlg.font())
        min_width = max(fm.horizontalAdvance(ln) for ln in lines) + 120
        dlg.setMinimumWidth(min_width)
        layout = QVBoxLayout(dlg)
        label = QLabel(help_html)
        label.setOpenExternalLinks(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        layout.addWidget(label)
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dlg.accept)
        layout.addWidget(ok_btn)
        dlg.exec()

    def _validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format."""
        if not api_key or len(api_key) < 20:
            return False
        return api_key.startswith("sk-") or len(api_key) > 40
    
    def _on_api_key_input_changed(self):
        """When user clears the API key field, remove saved key and allow submitting a new one."""
        text = self.api_key_input.text().strip()
        if text == "":
            self.api_key_manager.clear_api_key()
            self.api_key = None
            self.submit_api_key_btn.setEnabled(True)
            self.submit_api_key_btn.setText("Submit API Key")
            self.api_key_input.setToolTip("Enter your OpenAI API key...")
        elif self.api_key:
            # User edited the field away from the masked key; allow submit for new key
            masked = self.api_key[:7] + "*" * (len(self.api_key) - 11) + self.api_key[-4:]
            if text != masked:
                self.submit_api_key_btn.setEnabled(True)
                self.submit_api_key_btn.setText("Submit API Key")
    
    def _handle_api_key_submit(self):
        """Handle API key submission and start servers."""
        api_key = self.api_key_input.text().strip()
        
        logger.info("=" * 80)
        logger.info(f"[NLQueryDialog] API key submission initiated")
        logger.info(f"[NLQueryDialog] API key length: {len(api_key)}")
        logger.info(f"[NLQueryDialog] API key preview: {api_key[:7]}...{api_key[-4:] if len(api_key) > 11 else ''}")
        
        if not self._validate_api_key_format(api_key):
            logger.warning("[NLQueryDialog] API key validation failed")
            QMessageBox.warning(self, "Invalid API Key", 
                              "API key must start with 'sk-' or be at least 40 characters long.")
            return
        
        logger.info("[NLQueryDialog] API key format validated successfully")
        self.api_key = api_key
        
        # Save API key (encrypted)
        if self.api_key_manager.save_api_key(api_key):
            logger.info("[NLQueryDialog] API key saved successfully (encrypted)")
        else:
            logger.warning("[NLQueryDialog] Failed to save API key, but continuing...")
        
        self.submit_api_key_btn.setEnabled(False)
        self.submit_api_key_btn.setText("Starting Servers...")
        self.restart_servers_btn.setEnabled(False)  # Disable during startup
        self.stop_servers_btn.setEnabled(False)  # Disable during startup
        self._servers_ready_message_shown = False  # Allow one "Servers Ready" message this cycle
        self._servers_starting = True  # So failure handlers can clear and re-enable button
        
        # Start servers using GlobalServerManager
        logger.info("[NLQueryDialog] Calling GlobalServerManager.start_servers()...")
        if self.global_server_manager.start_servers(api_key, parent=self):
            logger.info("[NLQueryDialog] GlobalServerManager.start_servers() returned True")
            # Solution 1: Defer post-start work so 300 ms in-process timer can run
            QTimer.singleShot(0, self._on_start_servers_post_start)
        else:
            logger.error("[NLQueryDialog] GlobalServerManager.start_servers() returned False")
            QMessageBox.critical(self, "Server Error", 
                                "Failed to start servers. Please check the logs.")
            self.submit_api_key_btn.setEnabled(True)
            self.submit_api_key_btn.setText("Submit API Key")
        
        # Enable restart button after API key is set (even if servers fail, user can restart)
        # This will be updated when servers are ready or fail

    def _stop_servers_starting_poll(self):
        """Issue 4: Stop periodic is_servers_running poll when ready or failed."""
        if getattr(self, '_servers_starting_poll_timer', None) is not None:
            try:
                self._servers_starting_poll_timer.stop()
            except Exception:
                pass
            self._servers_starting_poll_timer = None
        if getattr(self, '_servers_starting_poll_stop_timer', None) is not None:
            try:
                self._servers_starting_poll_stop_timer.stop()
            except Exception:
                pass
            self._servers_starting_poll_stop_timer = None

    def _on_start_servers_post_start(self):
        """Solution 1: Run after start_servers() return so 300 ms server timer can fire."""
        self.server_manager = self.global_server_manager.get_server_manager()
        if self.server_manager:
            logger.info("[NLQueryDialog] Server manager instance obtained")
            self._connect_server_signals()
            logger.info("[NLQueryDialog] Server signals connected")
            self._update_server_status_icon(False)
            # If servers were already running (e.g. start_servers() returned without starting),
            # all_servers_ready was emitted in the past so we never get it; sync UI now.
            if self.global_server_manager.is_servers_running():
                logger.info("[NLQueryDialog] Servers already running, syncing UI to ready state")
                self._on_servers_ready()
            else:
                # Issue 4: periodic check in case ready signal was missed
                self._stop_servers_starting_poll()
                self._servers_starting_poll_timer = QTimer(self)
                self._servers_starting_poll_timer.timeout.connect(self._on_servers_starting_poll)
                self._servers_starting_poll_timer.start(1500)
                self._servers_starting_poll_stop_timer = QTimer(self)
                self._servers_starting_poll_stop_timer.setSingleShot(True)
                self._servers_starting_poll_stop_timer.timeout.connect(self._stop_servers_starting_poll)
                self._servers_starting_poll_stop_timer.start(40000)
        else:
            logger.warning("[NLQueryDialog] Server manager instance is None after start_servers()")

    def _on_servers_starting_poll(self):
        """Issue 4: If servers became ready without signal, sync UI."""
        if not getattr(self, '_servers_starting', False):
            return
        if self.global_server_manager.is_servers_running():
            self._stop_servers_starting_poll()
            self._on_servers_ready()

    def _handle_stop_servers(self):
        """Handle stop servers button click."""
        if not self.server_manager:
            QMessageBox.information(self, "No Servers", "No servers are currently running.")
            return
        
        reply = QMessageBox.question(
            self,
            "Stop Servers",
            "Are you sure you want to stop both servers?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._stop_servers()
    
    def _stop_servers(self):
        """Stop both servers and reset UI state."""
        # Stop servers via GlobalServerManager
        self.global_server_manager.stop_servers()
        self.server_manager = None
        
        # Update status icon
        self._update_server_status_icon(False)
        
        # Reset UI state
        self.submit_api_key_btn.setEnabled(True)
        self.submit_api_key_btn.setText("Submit API Key")
        self.stop_servers_btn.setEnabled(False)
        self.restart_servers_btn.setEnabled(True)  # Can restart if API key was submitted
        
        # Disable NL query section
        self.nl_query_input.setEnabled(False)
        self.submit_nl_query_btn.setEnabled(False)
        
        # Clear SQL display and results
        self.sql_display.clear()
        self.execute_sql_btn.setEnabled(False)
        self.results_table.setModel(None)
        self.query_results_df = None
        self._original_dataframe = None
        self.visualize_btn.setEnabled(False)
        
        # Clear failure states
        self._fastapi_failure_msg = None
        self._mcp_failure_msg = None
        self._stop_servers_starting_poll()
        self._servers_starting = False
        self._servers_ready_message_shown = False  # Reset so next start can show message once
        
        QMessageBox.information(self, "Servers Stopped", "Both servers have been stopped.")
    
    def _handle_restart_servers(self):
        """Handle restart servers button click."""
        if not self.api_key:
            QMessageBox.warning(
                self,
                "No API Key",
                "No API key available. Please submit an API key first."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Restart Servers",
            "Restart both servers using the current API key?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._restart_servers()
    
    def _restart_servers(self):
        """Stop and restart both servers using existing API key."""
        # Stop servers via GlobalServerManager
        self.global_server_manager.stop_servers()
        self.server_manager = None
        
        # Small delay to ensure clean shutdown
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self._restart_servers_after_stop)
    
    def _restart_servers_after_stop(self):
        """Called after servers are stopped to restart them."""
        # Update UI
        self.submit_api_key_btn.setEnabled(False)
        self.submit_api_key_btn.setText("Restarting Servers...")
        self.stop_servers_btn.setEnabled(False)
        self.restart_servers_btn.setEnabled(False)
        
        # Disable NL query section during restart
        self.nl_query_input.setEnabled(False)
        self.submit_nl_query_btn.setEnabled(False)
        
        # Clear SQL display and results
        self.sql_display.clear()
        self.execute_sql_btn.setEnabled(False)
        self.results_table.setModel(None)
        self.query_results_df = None
        self._original_dataframe = None
        self.visualize_btn.setEnabled(False)
        
        self._servers_ready_message_shown = False  # Allow one "Servers Ready" message after restart
        
        # Start servers using GlobalServerManager
        if self.api_key and self.global_server_manager.start_servers(self.api_key, parent=self):
            self.server_manager = self.global_server_manager.get_server_manager()
            if self.server_manager:
                self._connect_server_signals()
                self._update_server_status_icon(False)  # Will update when ready
        else:
            QMessageBox.critical(self, "Server Error", 
                                "Failed to restart servers. Please check the logs.")
            self.submit_api_key_btn.setEnabled(True)
            self.submit_api_key_btn.setText("Submit API Key")
    
    def _start_servers(self):
        """Start both FastAPI and MCP servers using the current API key."""
        try:
            if not self.server_manager:
                self.server_manager = NLServerManager(parent=self)
                # Connect all signals for server status
                self.server_manager.all_servers_ready.connect(self._on_servers_ready)
                self.server_manager.fastapi_ready.connect(self._on_fastapi_ready)
                self.server_manager.mcp_ready.connect(self._on_mcp_ready)
                self.server_manager.fastapi_failed.connect(self._on_fastapi_failed)
                self.server_manager.mcp_failed.connect(self._on_mcp_failed)
            
            # Set API key in environment BEFORE starting servers
            os.environ['OPENAI_API_KEY'] = self.api_key
            
            # Clear previous failure states
            self._fastapi_failure_msg = None
            self._mcp_failure_msg = None
            self._servers_starting = True
            
            # Start both servers
            self.server_manager.start_fastapi_server(
                output_callback=self._on_fastapi_output,
                error_callback=self._on_fastapi_error
            )
            self.server_manager.start_mcp_server(
                output_callback=self._on_mcp_output,
                error_callback=self._on_mcp_error
            )
        except Exception as e:
            logger.error(f"Failed to start servers: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Server Error", 
                                f"Failed to start servers: {str(e)}")
            self.submit_api_key_btn.setEnabled(True)
            self.submit_api_key_btn.setText("Submit API Key")
            self.stop_servers_btn.setEnabled(False)
            self.restart_servers_btn.setEnabled(True)  # Can restart with existing API key
    
    def _on_fastapi_output(self, text: str):
        """Handle FastAPI server output."""
        # Can be used for logging if needed
        pass
    
    def _on_fastapi_error(self, text: str):
        """Handle FastAPI server error output."""
        # Errors are handled by fastapi_failed signal
        pass
    
    def _on_mcp_output(self, text: str):
        """Handle MCP server output."""
        # Can be used for logging if needed
        pass
    
    def _on_mcp_error(self, text: str):
        """Handle MCP server error output."""
        # Errors are handled by mcp_failed signal
        pass
    
    def _on_servers_ready(self):
        """Called when both servers are ready."""
        self._stop_servers_starting_poll()
        self._servers_starting = False
        self._fastapi_failure_msg = None  # Clear any stored failures
        self._mcp_failure_msg = None
        
        # Ensure server_manager is set (in case it wasn't set during startup)
        if not self.server_manager:
            self.server_manager = self.global_server_manager.get_server_manager()
            if self.server_manager:
                self._connect_server_signals()
        
        self.submit_api_key_btn.setText("API Key Validated ✓")
        self.submit_api_key_btn.setEnabled(False)
        
        # Mask API key (field stays editable so user can clear to enter a different key)
        if self.api_key:
            masked = self.api_key[:7] + "*" * (len(self.api_key) - 11) + self.api_key[-4:]
            self.api_key_input.setText(masked)
            self.api_key_input.setToolTip("Clear the field to remove the saved key and enter a different one.")
        
        # Enable NL query section
        self.nl_query_input.setEnabled(True)
        self.submit_nl_query_btn.setEnabled(True)
        
        # Update status icon to green (running)
        self._update_server_status_icon(True)
        
        # Show success message only once (signal can fire from both dialog and GlobalServerManager)
        if not self._servers_ready_message_shown:
            self._servers_ready_message_shown = True
            QMessageBox.information(self, "Servers Ready", 
                                  "Both servers are ready. You can now submit queries.")
        
        # Enable stop and restart buttons
        self.stop_servers_btn.setEnabled(True)
        self.restart_servers_btn.setEnabled(True)
    
    def _on_fastapi_ready(self):
        """Handle FastAPI server ready signal."""
        # Clear any stored failure for this server
        self._fastapi_failure_msg = None
        # Individual server ready - all_servers_ready will be called when both are ready
        pass
    
    def _on_mcp_ready(self):
        """Handle MCP server ready signal."""
        # Clear any stored failure for this server
        self._mcp_failure_msg = None
        # Individual server ready - all_servers_ready will be called when both are ready
        pass
    
    def _on_fastapi_failed(self, msg: str):
        """Handle FastAPI server failure - clear starting state and re-enable button."""
        if self._is_closing:
            return
        
        if self.server_manager and self.server_manager.is_fastapi_running():
            logger.warning(f"FastAPI failed signal received but server is running: {msg}")
            self._fastapi_failure_msg = None
            return
        
        self._fastapi_failure_msg = msg
        self._stop_servers_starting_poll()
        self._servers_starting = False  # So UI always recovers when servers fail
        logger.warning(f"FastAPI server failure: {msg}")
        
        self.submit_api_key_btn.setEnabled(True)
        self.submit_api_key_btn.setText("Submit API Key")
        self.stop_servers_btn.setEnabled(False)
        self.restart_servers_btn.setEnabled(True if self.api_key else False)
        # Solution 6: Show actual failure message for diagnosis
        if not self._mcp_failure_msg:
            detail = (msg[:800] + "…") if len(msg) > 800 else (msg or "Check the logs folder next to the app.")
            QMessageBox.warning(
                self,
                "Servers",
                "Servers could not be started.\n\n" + detail
            )
    
    def _on_mcp_failed(self, msg: str):
        """Handle MCP server failure - clear starting state and re-enable button."""
        if self._is_closing:
            return
        
        if self.server_manager and self.server_manager.is_mcp_running():
            logger.warning(f"MCP failed signal received but server is running: {msg}")
            self._mcp_failure_msg = None
            return
        
        self._mcp_failure_msg = msg
        self._stop_servers_starting_poll()
        self._servers_starting = False  # So UI always recovers when servers fail
        logger.warning(f"MCP server failure: {msg}")
        
        self.submit_api_key_btn.setEnabled(True)
        self.submit_api_key_btn.setText("Submit API Key")
        self.stop_servers_btn.setEnabled(False)
        self.restart_servers_btn.setEnabled(True if self.api_key else False)
        # Solution 6: Show actual failure message for diagnosis
        if not self._fastapi_failure_msg:
            detail = (msg[:800] + "…") if len(msg) > 800 else (msg or "Check the logs folder next to the app.")
            QMessageBox.warning(
                self,
                "Servers",
                "Servers could not be started.\n\n" + detail
            )
    
    def _handle_nl_query_submit(self):
        """Handle NL query submission - only generates SQL, doesn't execute."""
        query = self.nl_query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "Empty Query", "Please enter a natural language query.")
            return
        
        # Check server status before submitting query - show errors here if servers failed
        if not self._check_servers_before_query():
            return
        
        self.submit_nl_query_btn.setEnabled(False)
        self.submit_nl_query_btn.setText("Processing...")
        self.sql_display.clear()
        self.sql_display.setPlainText("Generating SQL query...")
        self.execute_sql_btn.setEnabled(False)
        self.results_table.setModel(None)
        self.query_results_df = None
        self._original_dataframe = None
        self.visualize_btn.setEnabled(False)
        
        # Verify API key is available before starting thread
        if not self.api_key:
            QMessageBox.critical(
                self,
                "No API Key",
                "API key is not available. Please submit your API key first."
            )
            self.submit_nl_query_btn.setEnabled(True)
            self.submit_nl_query_btn.setText("Submit NL Query")
            return
        
        # Log API key info (for debugging, without exposing full key)
        logger.debug(f"Starting NL query with API key length: {len(self.api_key)}")
        logger.debug(f"API key preview: {self.api_key[:7]}...{self.api_key[-4:]}")
        
        # Start query thread (only gets SQL, doesn't execute)
        self.query_thread = NLQueryThread(self.api_key, query, "http://localhost:8000")
        self.query_thread.finished.connect(self._on_query_complete)
        self.query_thread.start()
    
    def _check_servers_before_query(self) -> bool:
        """
        Check if servers are ready before submitting query.
        Show error messages here if servers failed during startup.
        
        Returns:
            True if servers are ready, False otherwise
        """
        # First, try to get server manager from GlobalServerManager if not set
        if not self.server_manager:
            self.server_manager = self.global_server_manager.get_server_manager()
        
        # Check if servers are running via GlobalServerManager (more reliable)
        if not self.global_server_manager.is_servers_running():
            # Also check if server_manager exists but servers aren't running
            if not self.server_manager:
                QMessageBox.critical(
                    self,
                    "Servers Not Started",
                    "Servers have not been started. Please submit your API key first."
                )
                return False
            else:
                # Server manager exists but servers aren't running
                QMessageBox.critical(
                    self,
                    "Servers Not Running",
                    "Servers are not currently running. Please wait for servers to start or restart them."
                )
                return False
        
        # Check for stored failure messages
        errors = []
        if self._fastapi_failure_msg:
            errors.append(f"FastAPI Server: {self._fastapi_failure_msg}")
        if self._mcp_failure_msg:
            errors.append(f"MCP Server: {self._mcp_failure_msg}")
        
        # Check actual server status
        fastapi_running = self.server_manager.is_fastapi_running()
        mcp_running = self.server_manager.is_mcp_running()
        
        if not fastapi_running or not mcp_running:
            # Build error message
            error_msg = "Cannot submit query - servers are not running.\n\n"
            
            if errors:
                error_msg += "Server startup errors:\n"
                for error in errors:
                    error_msg += f"  • {error}\n"
                error_msg += "\n"
            
            if not fastapi_running:
                error_msg += "• FastAPI server is not running\n"
                if not mcp_running:
                    error_msg += "\n"
            if not mcp_running:
                error_msg += "• MCP server is not running\n"
            
            error_msg += "\nPlease check your API key and try starting the servers again."
            
            QMessageBox.critical(
                self,
                "Servers Not Ready",
                error_msg
            )
            return False
        
        # Servers are running - clear any stored failures
        if self._fastapi_failure_msg or self._mcp_failure_msg:
            logger.info("Servers are running - clearing stored failure messages")
            self._fastapi_failure_msg = None
            self._mcp_failure_msg = None
        
        return True
    
    def _on_query_complete(self, sql_query: Optional[str]):
        """Handle SQL query generation completion."""
        self.submit_nl_query_btn.setEnabled(True)
        self.submit_nl_query_btn.setText("Submit NL Query")
        
        # Handle None result (error occurred)
        if sql_query is None or not sql_query.strip():
            QMessageBox.warning(self, "Query Failed", 
                              "Failed to generate SQL query. Please check your query and try again.\n\n"
                              "Common issues:\n"
                              "- Server may not be ready yet\n"
                              "- Invalid query format\n"
                              "- Network connection error")
            self.sql_display.clear()
            return
        
        # Store SQL for execution
        self.current_sql = sql_query.strip()
        logger.info(f"[Query Complete] Received SQL query (length: {len(self.current_sql)})")
        logger.info(f"[Query Complete] SQL preview: {self.current_sql[:100]}...")
        
        # Format SQL for display
        formatted_sql = self._format_sql(self.current_sql)
        logger.info(f"[Query Complete] Formatted SQL (length: {len(formatted_sql)})")
        logger.info(f"[Query Complete] Formatted SQL preview:\n{formatted_sql[:200]}...")
        
        # Display formatted SQL in panel (CRITICAL: This must happen before caching)
        logger.info(f"[Query Complete] Setting sql_display text...")
        logger.info(f"[Query Complete] sql_display widget state: enabled={self.sql_display.isEnabled()}, visible={self.sql_display.isVisible()}")
        
        self.sql_display.setPlainText(formatted_sql)
        self.sql_display.setEnabled(True)
        
        # Verify text was set correctly
        displayed_text = self.sql_display.toPlainText()
        if displayed_text == formatted_sql:
            logger.info(f"[Query Complete] ✅ Formatted SQL successfully displayed in panel (length: {len(displayed_text)})")
        else:
            logger.warning(f"[Query Complete] ⚠️ Text mismatch! Expected {len(formatted_sql)} chars, got {len(displayed_text)} chars")
            logger.warning(f"[Query Complete] Expected preview: {formatted_sql[:100]}...")
            logger.warning(f"[Query Complete] Actual preview: {displayed_text[:100]}...")
            # Try setting again
            self.sql_display.setPlainText(formatted_sql)
            self.sql_display.update()
            self.sql_display.repaint()
        
        # Enable execute button so user can run the query
        self.execute_sql_btn.setEnabled(True)
        logger.info(f"[Query Complete] Execute button enabled")
        
        # Cache the query (non-blocking, with error handling)
        # Mark as new query (not from cache)
        self._is_cached_query = False
        
        # NOTE: formatted_sql is already computed and displayed above
        if sql_query and sql_query.strip() and self.query_cache is not None:
            try:
                logger.info(f"[Query Complete] Caching query with formatted_sql (length: {len(formatted_sql)})")
                cache_id = self.query_cache.add_query(
                    nl_query=self.nl_query_input.toPlainText().strip(),
                    sql_query=self.current_sql,
                    formatted_sql=formatted_sql  # Use the same formatted_sql that was displayed
                )
                logger.info(f"[Query Complete] ✅ Query cached successfully (ID: {cache_id})")
                # Defer dropdown refresh to avoid blocking UI
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self._refresh_cache_dropdown)
            except Exception as e:
                logger.error(f"[Query Complete] ❌ Failed to cache query: {e}", exc_info=True)
                # Continue without caching - don't block user
        else:
            if not sql_query or not sql_query.strip():
                logger.warning(f"[Query Complete] Not caching: sql_query is empty")
            if self.query_cache is None:
                logger.warning(f"[Query Complete] Not caching: query_cache is None")
        
        # Clear previous results
        self.results_table.setModel(None)
        self.query_results = None
        self.query_results_df = None
        self._original_dataframe = None
        self.visualize_btn.setEnabled(False)
    
    def _format_sql(self, sql: str) -> str:
        """Format SQL for display."""
        if not sql.strip().upper().startswith("SELECT"):
            return sql
        
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER JOIN', 
                   'LEFT JOIN', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT']
        
        formatted = sql.strip()
        for keyword in keywords:
            formatted = formatted.replace(f' {keyword} ', f'\n{keyword} ')
            formatted = formatted.replace(f' {keyword.lower()} ', f'\n{keyword.upper()} ')
        
        while '\n\n' in formatted:
            formatted = formatted.replace('\n\n', '\n')
        
        return formatted.strip()
    
    def _display_dataframe(self, df: pd.DataFrame):
        """Display pandas DataFrame in QTableView."""
        if df is None or df.empty:
            self.results_status_label.setText("Query returned no results.")
            self.results_status_label.setVisible(True)
            self.results_table.setModel(None)
            self.visualize_btn.setEnabled(False)
            return
        
        # Create and set model
        model = PandasTableModel(df, parent=self)
        self.results_table.setModel(model)
        
        # Resize columns to fit content
        self.results_table.resizeColumnsToContents()
        
        # Update status label
        row_count = len(df)
        col_count = len(df.columns)
        memory_kb = df.memory_usage(deep=True).sum() / 1024
        self.results_status_label.setText(
            f"Total rows: {row_count:,} | Columns: {col_count} | "
            f"Memory: {memory_kb:.2f} KB"
        )
        self.results_status_label.setVisible(True)
        
        # Enable table and visualize button when we have data
        self.results_table.setEnabled(True)
        self.visualize_btn.setEnabled(True)
    
    def _refresh_cache_dropdown(self):
        """Refresh the cached queries dropdown with current cache."""
        # Preserve currently selected query to avoid clearing SQL display
        current_selection = None
        current_index = self.query_cache_combo.currentIndex()
        if current_index >= 0:
            current_selection = self.query_cache_combo.itemData(current_index)
        
        if self.query_cache is None:
            # Cache not available, show empty state
            self.query_cache_combo.clear()
            self.query_cache_combo.addItem("Cache unavailable", None)
            self.query_cache_combo.setEnabled(False)
            if hasattr(self, 'cache_size_label'):
                self.cache_size_label.setText("Cache: unavailable")
            return
        
        self.query_cache_combo.clear()
        
        try:
            cached_queries = self.query_cache.get_all_queries()
        except Exception as e:
            logger.warning(f"Failed to get cached queries: {e}", exc_info=True)
            self.query_cache_combo.addItem("Error loading cache", None)
            self.query_cache_combo.setEnabled(False)
            return
        
        # Update cache size label in toolbar
        if hasattr(self, 'cache_size_label'):
            cache_count = len(cached_queries)
            max_size = self.query_cache.max_size
            self.cache_size_label.setText(f"Cache: {cache_count}/{max_size}")
        
        if not cached_queries:
            self.query_cache_combo.addItem("No cached queries", None)
            # Keep dropdown enabled (user might want to see empty state)
            self.query_cache_combo.setEnabled(True)
            if hasattr(self, 'clear_cache_btn'):
                self.clear_cache_btn.setEnabled(False)
            return
        
        # Add placeholder option first (only one)
        self.query_cache_combo.addItem("Select a cached query...", None)
        
        # Add cached queries to dropdown
        restored_index = 0  # Default to placeholder
        for query in cached_queries:
            display_text = f"{query['display_name']} ({self._format_timestamp(query['timestamp'])})"
            item_index = self.query_cache_combo.count()
            self.query_cache_combo.addItem(display_text, query['id'])
            # Add tooltip with full NL query
            self.query_cache_combo.setItemData(item_index, query['nl_query'], Qt.ToolTipRole)
            
            # Restore selection if this was the previously selected query
            if current_selection and query['id'] == current_selection:
                restored_index = item_index
        
        # Always enable dropdown (no API key required)
        self.query_cache_combo.setEnabled(True)
        if hasattr(self, 'clear_cache_btn'):
            self.clear_cache_btn.setEnabled(True)
        
        # Restore previous selection (or set to placeholder)
        # Block signals temporarily to avoid triggering _on_cached_query_selected
        self.query_cache_combo.blockSignals(True)
        self.query_cache_combo.setCurrentIndex(restored_index)
        self.query_cache_combo.blockSignals(False)
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp to readable string."""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "Unknown"
    
    def _on_cached_query_selected(self, index: int):
        """Handle selection of cached query from dropdown."""
        if index < 0:
            return
        
        # Skip placeholder item (first item with None data)
        cache_id = self.query_cache_combo.itemData(index)
        if not cache_id:
            # Placeholder selected - only clear if user explicitly selected it
            # Don't clear if this was triggered by refresh or during execution
            # Don't clear SQL display if it has content - preserve it
            
            # Check if SQL display has content - if so, preserve it
            # Only clear if display is already empty or user explicitly wants to clear
            if self.sql_display.toPlainText().strip():
                # SQL display has content - don't clear automatically
                # User can manually clear if needed
                logger.info("[Cached Query Selected] Preserving SQL display (has content)")
                # Close the dropdown after selection using QTimer to ensure it happens after event processing
                from PySide6.QtCore import QTimer
                QTimer.singleShot(10, lambda: self.query_cache_combo.hidePopup())
                return
            
            # User explicitly selected placeholder and display is empty - clear everything
            self.sql_display.clear()
            self.current_sql = None
            self._is_cached_query = False  # Reset cached query flag
            self.execute_sql_btn.setEnabled(False)  # For new queries (needs API key)
            self.results_table.setModel(None)
            self.results_status_label.setText("Select a cached query to view or execute...")
            self.results_status_label.setVisible(True)
            # Close the dropdown after selection using QTimer to ensure it happens after event processing
            from PySide6.QtCore import QTimer
            QTimer.singleShot(10, lambda: self.query_cache_combo.hidePopup())
            return
        
        if self.query_cache is None:
            QMessageBox.warning(self, "Cache Unavailable", "Query cache is not available.")
            # Close dropdown even on error
            from PySide6.QtCore import QTimer
            QTimer.singleShot(10, lambda: self.query_cache_combo.hidePopup())
            return
        
        cached_query = self.query_cache.get_query(cache_id)
        if not cached_query:
            QMessageBox.warning(self, "Cache Error", "Selected query not found in cache.")
            # Close dropdown even on error
            from PySide6.QtCore import QTimer
            QTimer.singleShot(10, lambda: self.query_cache_combo.hidePopup())
            return
        
        # Populate SQL display with cached formatted SQL (right below dropdown in right panel)
        self.sql_display.setPlainText(cached_query["formatted_sql"])
        self.sql_display.setEnabled(True)  # Enable for viewing/editing
        self.current_sql = cached_query["sql_query"]  # Store raw SQL for execution
        self._is_cached_query = True  # Mark as cached query for local execution
        
        # Enable execute button - cached queries can execute locally without API key
        self.execute_sql_btn.setEnabled(True)
        
        # Clear previous results
        self.results_table.setModel(None)
        self.results_status_label.setText("Cached query loaded. Use 'Execute SQL Query' button to run it (requires API key).")
        self.results_status_label.setVisible(True)
        
        # Close the dropdown after selection using QTimer to ensure it happens after event processing
        # This prevents the popup from staying visible behind the dialog
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, lambda: self.query_cache_combo.hidePopup())
    
    def _handle_clear_cache(self):
        """Handle clear cache button click."""
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "Are you sure you want to clear all cached queries?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.query_cache is not None:
                try:
                    self.query_cache.clear_cache()
                    self._refresh_cache_dropdown()
                except Exception as e:
                    logger.warning(f"Failed to clear cache: {e}", exc_info=True)
                    QMessageBox.warning(self, "Cache Error", f"Failed to clear cache: {str(e)}")
            else:
                QMessageBox.information(self, "Cache Unavailable", "Cache is not available.")
            QMessageBox.information(self, "Cache Cleared", "All cached queries have been cleared.")
    
    
    def _generate_descriptive_filename(self, nl_query: Optional[str] = None) -> str:
        """Generate a descriptive filename from NL query or use fallback."""
        if nl_query:
            # Extract first 5 words from NL query
            words = nl_query.lower().split()[:5]
            summary = "_".join(words)
            # Sanitize: remove special chars, limit length
            summary = "".join(c if c.isalnum() or c == "_" else "" for c in summary)[:40]
            if summary:
                return f"query_{summary}"
        
        # Fallback to generic name
        return "query"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be filesystem-safe."""
        # Remove/replace filesystem-unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        # Limit total length (Windows: 260 chars, but we'll be more conservative)
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def _get_unique_filename(self, directory: Path, base_filename: str, extension: str = ".csv") -> Path:
        """Get a unique filename by appending (1), (2), etc. if duplicates exist."""
        base_filename = self._sanitize_filename(base_filename)
        full_filename = f"{base_filename}{extension}"
        file_path = directory / full_filename
        
        # If file doesn't exist, return it
        if not file_path.exists():
            return file_path
        
        # If file exists, append (1), (2), etc.
        counter = 1
        while file_path.exists():
            new_filename = f"{base_filename}({counter}){extension}"
            file_path = directory / new_filename
            counter += 1
        
        return file_path
    
    def _get_date_folder(self, base_dir: Path) -> Path:
        """Get or create date-based folder (YYYY-MM-DD format)."""
        date_str = datetime.now().strftime('%Y-%m-%d')
        date_folder = base_dir / date_str
        date_folder.mkdir(parents=True, exist_ok=True)
        return date_folder
    
    def _get_nl_query_for_export(self) -> Optional[str]:
        """Get the NL query for export (from input or cache)."""
        # Try to get from input field
        nl_query = self.nl_query_input.toPlainText().strip()
        if nl_query:
            return nl_query
        
        # Try to get from cache if current SQL matches a cached query
        if self.current_sql and self.query_cache:
            try:
                # Search through all cached queries to find one matching current SQL
                all_queries = self.query_cache.get_all_queries()
                for cached_query in all_queries:
                    if cached_query.get("sql_query") == self.current_sql:
                        return cached_query.get("nl_query")
            except Exception as e:
                logger.warning(f"Failed to search cache for NL query: {e}", exc_info=True)
        
        return None
    
    def _handle_visualize(self):
        """Open visualization options and show chart from query results."""
        if self.query_results_df is None or self.query_results_df.empty:
            QMessageBox.warning(
                self,
                "No Results",
                "No query results to visualize. Execute a SQL query first."
            )
            return
        try:
            opts_dialog = VizOptionsDialog(self.query_results_df, parent=self)
            if opts_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            options = opts_dialog.get_options()
            fig = build_figure(self.query_results_df.copy(), options)
            viewer = VizViewerDialog(parent=self)
            viewer.set_figure(fig)
            viewer.exec()
        except Exception as e:
            logger.exception("Visualization failed")
            QMessageBox.warning(
                self,
                "Visualization Error",
                f"Could not create chart: {str(e)}"
            )
    
    def _handle_export_query_results(self):
        """Export formatted SQL query and results to separate folders."""
        # Check if we have a query
        if not self.current_sql:
            QMessageBox.warning(
                self,
                "No Query",
                "No query available to export. Please select or generate a query first."
            )
            return
        
        # Get formatted SQL
        formatted_sql = self.sql_display.toPlainText()
        
        # Get results (if available) - use DataFrame if available, otherwise list
        has_results = False
        if self.query_results_df is not None and not self.query_results_df.empty:
            has_results = True
        elif self.query_results is not None and len(self.query_results) > 0:
            has_results = True
        
        # Create base export directories if they don't exist
        formatted_base_dir = get_data_path("exports", "nl_queries", "formatted")
        results_base_dir = get_data_path("exports", "nl_queries", "results")
        formatted_base_dir.mkdir(parents=True, exist_ok=True)
        results_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Get or create date folders
        formatted_date_dir = self._get_date_folder(formatted_base_dir)
        results_date_dir = self._get_date_folder(results_base_dir)
        
        # Get NL query for descriptive naming
        nl_query = self._get_nl_query_for_export()
        
        # Generate descriptive base filename
        base_filename = self._generate_descriptive_filename(nl_query)
        
        try:
            # Export 1: Formatted SQL Query to formatted/date folder
            formatted_path = self._get_unique_filename(formatted_date_dir, base_filename, ".csv")
            
            with open(formatted_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Section 1: Query Metadata
                writer.writerow(["Formatted SQL Query Export"])
                writer.writerow(["Export Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(["Raw SQL", self.current_sql])  # Include raw SQL for reference
                writer.writerow([])  # Empty row
                
                # Section 2: Formatted SQL Query (line by line)
                writer.writerow(["Formatted SQL Query"])
                writer.writerow([])  # Empty row
                for line in formatted_sql.split('\n'):
                    writer.writerow([line])
                writer.writerow([])  # Empty row
                writer.writerow(["End of Export"])
            
            # Export 2: Query Results to results/date folder (if available)
            results_path = None
            if has_results:
                # Use same base filename for results
                results_path = self._get_unique_filename(results_date_dir, base_filename, ".csv")
                
                # Use DataFrame if available (better CSV handling)
                if self.query_results_df is not None and not self.query_results_df.empty:
                    self.query_results_df.to_csv(results_path, index=False, encoding='utf-8')
                elif self.query_results:
                    # Fallback to list-based export
                    with open(results_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        
                        # Write headers
                        headers = list(self.query_results[0].keys())
                        writer.writerow(headers)
                        
                        # Write data rows
                        for row in self.query_results:
                            writer.writerow([row.get(header, '') for header in headers])
            
            # Success message
            date_str = datetime.now().strftime('%Y-%m-%d')
            message = f"Export successful!\n\n"
            message += f"Formatted Query:\n{formatted_path.name}\n"
            message += f"Location: data/exports/nl_queries/formatted/{date_str}/\n\n"
            
            if results_path:
                message += f"Query Results:\n{results_path.name}\n"
                message += f"Location: data/exports/nl_queries/results/{date_str}/"
            else:
                message += "Query Results: Not exported (no results available)"
            
            QMessageBox.information(
                self,
                "Export Successful",
                message
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export query and results:\n{str(e)}"
            )
    
    def _handle_import_queries_csv(self):
        """Import formatted SQL queries from CSV file into cache."""
        # Default to formatted queries directory (not results directory)
        # Use today's date folder as default, but allow browsing to any date folder
        formatted_base_dir = get_data_path("exports", "nl_queries", "formatted")
        date_str = datetime.now().strftime('%Y-%m-%d')
        default_date_dir = formatted_base_dir / date_str
        # If today's folder doesn't exist, use base directory
        if not default_date_dir.exists():
            default_dir = str(formatted_base_dir)
        else:
            default_dir = str(default_date_dir)
        
        # Get file path using QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Formatted Queries from CSV",
            default_dir,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            imported_count = 0
            current_sql_lines = []
            in_sql_section = False
            raw_sql = None
            
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                
                for row in reader:
                    if not row:  # Empty row
                        continue
                    
                    row_text = row[0].strip() if row else ""
                    
                    # Detect raw SQL line
                    if row_text.startswith("Raw SQL"):
                        if len(row) > 1:
                            raw_sql = row[1].strip()
                        continue
                    
                    # Detect SQL query section
                    if "Formatted SQL Query" in row_text:
                        in_sql_section = True
                        current_sql_lines = []
                        continue
                    
                    # Detect end of SQL section (empty row or next section)
                    if in_sql_section:
                        if "Query Results" in row_text or "End of Export" in row_text:
                            # Save current query if we have SQL
                            if current_sql_lines:
                                formatted_sql = '\n'.join(current_sql_lines).strip()
                                if formatted_sql:
                                    # Use raw SQL if available, otherwise extract from formatted
                                    if not raw_sql:
                                        raw_sql = self._extract_raw_sql(formatted_sql)
                                    
                                    # Create display name from first line or SQL
                                    display_name = formatted_sql.split('\n')[0][:50]
                                    if not display_name:
                                        display_name = raw_sql[:50] if raw_sql else "Imported query"
                                    
                                    # Add to cache
                                    if self.query_cache is not None:
                                        try:
                                            self.query_cache.add_query(
                                                nl_query=f"Imported from CSV: {Path(file_path).name}",
                                                sql_query=raw_sql or formatted_sql,
                                                formatted_sql=formatted_sql
                                            )
                                            imported_count += 1
                                        except Exception as e:
                                            logger.warning(f"Failed to cache imported query: {e}", exc_info=True)
                            
                            in_sql_section = False
                            current_sql_lines = []
                            raw_sql = None
                            continue
                        
                        # Collect SQL lines (skip metadata rows)
                        if row_text and not row_text.startswith("[") and "Export" not in row_text:
                            current_sql_lines.append(row_text)
            
            # Handle last query if file ends without "End of Export"
            if in_sql_section and current_sql_lines:
                formatted_sql = '\n'.join(current_sql_lines).strip()
                if formatted_sql:
                    if not raw_sql:
                        raw_sql = self._extract_raw_sql(formatted_sql)
                    display_name = formatted_sql.split('\n')[0][:50] or (raw_sql[:50] if raw_sql else "Imported query")
                    if self.query_cache is not None:
                        try:
                            self.query_cache.add_query(
                                nl_query=f"Imported from CSV: {Path(file_path).name}",
                                sql_query=raw_sql or formatted_sql,
                                formatted_sql=formatted_sql
                            )
                            imported_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to cache imported query: {e}", exc_info=True)
            
            # Refresh dropdown
            self._refresh_cache_dropdown()
            
            QMessageBox.information(
                self,
                "Import Successful",
                f"Successfully imported {imported_count} query/queries from:\n{file_path}"
            )
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import queries from CSV:\n{str(e)}"
            )
    
    def _extract_raw_sql(self, formatted_sql: str) -> str:
        """Extract raw SQL from formatted SQL (remove extra whitespace/newlines)."""
        # Remove excessive newlines and whitespace
        lines = [line.strip() for line in formatted_sql.split('\n') if line.strip()]
        # Join with single spaces, preserving SQL keywords
        raw_sql = ' '.join(lines)
        # Clean up multiple spaces
        raw_sql = re.sub(r'\s+', ' ', raw_sql)
        return raw_sql.strip()

    def _is_sql_safe_for_local_execute(self, sql: str) -> Tuple[bool, str]:
        """
        Check if SQL is allowed for local execution (SELECT only, no dangerous keywords).
        Returns (True, "") if safe; (False, reason) if not.
        """
        if not sql or not sql.strip():
            return False, "Empty query."
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            return False, "Only SELECT queries are allowed for Execute SQL."
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Dangerous operation detected: {keyword}"
        return True, ""

    def _handle_execute_sql(self):
        """Handle SQL execution - runs query on database and displays results in bottom right."""
        if not self.current_sql:
            QMessageBox.warning(self, "No SQL Query", "No SQL query available to execute.")
            return
        
        # Safety: only allow SELECT; reject dangerous keywords (same policy as MCP /execute)
        ok, reason = self._is_sql_safe_for_local_execute(self.current_sql)
        if not ok:
            QMessageBox.warning(
                self,
                "Query Not Allowed",
                reason,
            )
            self.results_status_label.setText(reason)
            self.results_status_label.setVisible(True)
            return

        # Execute locally (cached and new formatted queries) — same DB path: get_database_path()
        logger.info("[Execute SQL] Executing query locally (League.db at get_database_path())")
        self.execute_sql_btn.setEnabled(False)
        self.execute_sql_btn.setText("Executing...")
        self.results_table.setModel(None)
        self.results_status_label.setText("Executing query...")
        self.results_status_label.setVisible(True)

        self.local_execute_thread = LocalSQLExecuteThread(self.current_sql)
        self.local_execute_thread.finished.connect(self._on_execution_complete)
        self.local_execute_thread.start()
    
    def _on_execution_complete(self, results: Optional[list]):
        """Handle SQL execution completion."""
        self.execute_sql_btn.setEnabled(True)
        self.execute_sql_btn.setText("Execute SQL Query")
        
        if results is None:
            QMessageBox.warning(self, "Execution Failed", 
                              "Failed to execute SQL query. Please check the query and try again.")
            self.results_status_label.setText("Execution failed. Please try again.")
            self.results_status_label.setVisible(True)
            return
        
        # Convert results to pandas DataFrame
        if not results:
            self.results_status_label.setText("Query returned no results.")
            self.results_status_label.setVisible(True)
            QMessageBox.information(self, "No Results", "Query returned no results.")
            self.query_results_df = None
            self._original_dataframe = None
            self.query_results = None
            self.visualize_btn.setEnabled(False)
            return
        
        try:
            # Convert list of dicts to DataFrame
            self.query_results_df = pd.DataFrame(results)
            self._original_dataframe = self.query_results_df.copy()  # Store original for filter reset
            
            # Store original list format for backward compatibility
            self.query_results = results
            
            # Display DataFrame in table view
            self._display_dataframe(self.query_results_df)
            
        except Exception as e:
            logger.error(f"Failed to create DataFrame: {e}", exc_info=True)
            QMessageBox.warning(self, "Data Error", 
                              f"Failed to process results: {str(e)}")
            self.query_results_df = None
            self._original_dataframe = None
            self.query_results = None
            self.visualize_btn.setEnabled(False)
    
    def closeEvent(self, event: QCloseEvent):
        """Handle dialog close - stop servers and save API key."""
        # Set closing flag to prevent error messages
        self._is_closing = True
        
        # Disconnect failure signal handlers to prevent error messages during shutdown
        if self.server_manager:
            try:
                self.server_manager.fastapi_failed.disconnect()
                self.server_manager.mcp_failed.disconnect()
            except (TypeError, RuntimeError):
                # Signals may not be connected, ignore
                pass
        
        # Stop any running threads
        if self.query_thread and self.query_thread.isRunning():
            self.query_thread.terminate()
            self.query_thread.wait(1000)  # Wait up to 1 second
        
        if self.execute_thread and self.execute_thread.isRunning():
            self.execute_thread.terminate()
            self.execute_thread.wait(1000)  # Wait up to 1 second
        
        if self.local_execute_thread and self.local_execute_thread.isRunning():
            self.local_execute_thread.terminate()
            self.local_execute_thread.wait(1000)  # Wait up to 1 second
        
        # Stop servers when dialog closes
        # API key remains on disk for the session; cleared when program exits
        if self.global_server_manager:
            logger.info("Dialog closing - stopping servers")
            self.global_server_manager.stop_servers()
        
        event.accept()
