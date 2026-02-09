"""
NL-to-SQL Query Dialog for natural language database queries.

Provides a GUI for natural language database queries using OpenAI and FastAPI.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QMessageBox, QHeaderView, QSplitter, QTableView,
    QComboBox, QAbstractItemView, QToolBar, QFileDialog
)
from PySide6.QtCore import QThread, Signal, Qt, QAbstractTableModel
from PySide6.QtGui import QCloseEvent, QAction, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QLabel
from src.utils.nl_sql_server import NLServerManager
from src.utils.nl_query_cache import NLQueryCache
from src.utils.path_resolver import get_data_path
from src.utils.api_key_manager import APIKeyManager
from src.utils.global_server_manager import GlobalServerManager
from typing import Optional
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


class NLQueryDialog(QDialog):
    """Dialog for NL-to-SQL queries."""
    
    # Signal emitted when query completes successfully
    query_completed = Signal(dict)  # {'sql': str, 'results': list}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NL-to-SQL Query")
        self.setMinimumSize(1000, 700)
        
        # Make dialog stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        # State
        self.api_key: Optional[str] = None
        self.server_manager: Optional[NLServerManager] = None
        self.query_thread: Optional[NLQueryThread] = None
        self.execute_thread: Optional[SQLExecuteThread] = None
        self.current_sql: Optional[str] = None
        self.query_results: Optional[list] = None  # Keep for backward compatibility
        self.query_results_df: Optional[pd.DataFrame] = None  # DataFrame storage
        self._original_dataframe: Optional[pd.DataFrame] = None  # Store original for filter reset
        self._is_closing = False  # Flag to prevent error messages during close
        
        # Server failure state (stored, not shown immediately)
        self._fastapi_failure_msg: Optional[str] = None
        self._mcp_failure_msg: Optional[str] = None
        self._servers_starting = False  # Track if servers are in startup phase
        
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
        
        # Create toolbar at top
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
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
    
    def _create_toolbar(self) -> QToolBar:
        """Create toolbar with search/filter and export functionality."""
        toolbar = QToolBar("Query Cache Tools", self)
        toolbar.setMovable(False)
        
        # Search/Filter Section
        toolbar.addWidget(QLabel("Search:"))
        self.search_filter_input = QLineEdit()
        self.search_filter_input.setPlaceholderText("Filter cached queries by NL query or SQL keywords...")
        self.search_filter_input.setMaximumWidth(300)
        self.search_filter_input.textChanged.connect(self._on_search_filter_changed)
        toolbar.addWidget(self.search_filter_input)
        
        # Separator
        toolbar.addSeparator()
        
        # Import/Export Section
        import_action = QAction("Import Queries from CSV", self)
        import_action.setToolTip("Import formatted SQL queries from CSV file (from formatted/ folder)")
        import_action.triggered.connect(self._handle_import_queries_csv)
        toolbar.addAction(import_action)
        
        export_action = QAction("Export Query & Results", self)
        export_action.setToolTip("Export formatted SQL query and results to separate folders")
        export_action.triggered.connect(self._handle_export_query_results)
        toolbar.addAction(export_action)
        
        # Cache size indicator
        toolbar.addSeparator()
        self.cache_size_label = QLabel("Cache: 0/50")
        toolbar.addWidget(self.cache_size_label)
        
        return toolbar
    
    def _create_right_panel(self) -> QWidget:
        """Create right panel with cached queries, SQL display, execute button, and results."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Cached Queries Section (top of right panel, above SQL display)
        # NOTE: This section is ALWAYS enabled, no API key required
        cached_label = QLabel("Load Cached Query:")
        self.query_cache_combo = QComboBox()
        self.query_cache_combo.setEditable(False)
        self.query_cache_combo.setPlaceholderText("Select a cached query...")
        self.query_cache_combo.currentIndexChanged.connect(self._on_cached_query_selected)
        # Cache dropdown is always enabled (independent of API key state)
        
        # Execute button for cached queries (works without API key)
        self.execute_cached_btn = QPushButton("Execute Cached Query")
        self.execute_cached_btn.clicked.connect(self._handle_execute_cached_query)
        self.execute_cached_btn.setEnabled(False)  # Enabled when cached query is selected
        
        # Clear cache button
        self.clear_cache_btn = QPushButton("Clear Cache")
        self.clear_cache_btn.clicked.connect(self._handle_clear_cache)
        self.clear_cache_btn.setEnabled(False)  # Disabled when cache is empty
        
        # Layout for cache controls
        cache_buttons_layout = QHBoxLayout()
        cache_buttons_layout.addWidget(cached_label)
        cache_buttons_layout.addWidget(self.query_cache_combo, stretch=1)
        cache_buttons_layout.addWidget(self.execute_cached_btn)
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
        
        self.execute_sql_btn = QPushButton("Execute SQL Query")
        self.execute_sql_btn.clicked.connect(self._handle_execute_sql)
        
        layout.addWidget(sql_label)
        layout.addWidget(self.sql_display)
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
        
        # Analysis buttons (below results table)
        analysis_layout = QHBoxLayout()
        analysis_layout.setSpacing(10)
        
        self.stats_btn = QPushButton("Show Statistics")
        self.stats_btn.clicked.connect(self._show_dataframe_stats)
        self.stats_btn.setEnabled(False)
        
        self.filter_btn = QPushButton("Filter Data")
        self.filter_btn.clicked.connect(self._show_filter_dialog)
        self.filter_btn.setEnabled(False)
        
        self.reset_filter_btn = QPushButton("Reset Filter")
        self.reset_filter_btn.clicked.connect(self._reset_filter)
        self.reset_filter_btn.setEnabled(False)
        
        analysis_layout.addWidget(self.stats_btn)
        analysis_layout.addWidget(self.filter_btn)
        analysis_layout.addWidget(self.reset_filter_btn)
        analysis_layout.addStretch()
        
        layout.addWidget(results_label)
        layout.addWidget(self.results_status_label)
        layout.addWidget(self.results_table)
        layout.addLayout(analysis_layout)
        
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
        if self.global_server_manager.is_servers_running():
            logger.info("Servers are already running, connecting to existing instance")
            self.server_manager = self.global_server_manager.get_server_manager()
            self._connect_server_signals()
            self._on_servers_ready()
        elif saved_api_key:
            # Servers not running but API key exists - offer to start
            logger.info("API key found but servers not running")
            # User can click "Submit API Key" to start servers
        
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
    
    def _validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format."""
        if not api_key or len(api_key) < 20:
            return False
        return api_key.startswith("sk-") or len(api_key) > 40
    
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
        
        # Start servers using GlobalServerManager
        logger.info("[NLQueryDialog] Calling GlobalServerManager.start_servers()...")
        if self.global_server_manager.start_servers(api_key, parent=self):
            logger.info("[NLQueryDialog] GlobalServerManager.start_servers() returned True")
            # Get the server manager instance
            self.server_manager = self.global_server_manager.get_server_manager()
            if self.server_manager:
                logger.info("[NLQueryDialog] Server manager instance obtained")
                self._connect_server_signals()
                logger.info("[NLQueryDialog] Server signals connected")
                # Update status icon
                self._update_server_status_icon(False)  # Will update when servers are ready
            else:
                logger.warning("[NLQueryDialog] Server manager instance is None after start_servers()")
        else:
            logger.error("[NLQueryDialog] GlobalServerManager.start_servers() returned False")
            QMessageBox.critical(self, "Server Error", 
                                "Failed to start servers. Please check the logs.")
            self.submit_api_key_btn.setEnabled(True)
            self.submit_api_key_btn.setText("Submit API Key")
        
        # Enable restart button after API key is set (even if servers fail, user can restart)
        # This will be updated when servers are ready or fail
    
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
        
        # Clear failure states
        self._fastapi_failure_msg = None
        self._mcp_failure_msg = None
        self._servers_starting = False
        
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
        
        # Mask API key
        if self.api_key:
            masked = self.api_key[:7] + "*" * (len(self.api_key) - 11) + self.api_key[-4:]
            self.api_key_input.setText(masked)
        self.api_key_input.setReadOnly(True)
        
        # Enable NL query section
        self.nl_query_input.setEnabled(True)
        self.submit_nl_query_btn.setEnabled(True)
        
        # Update status icon to green (running)
        self._update_server_status_icon(True)
        
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
        """Handle FastAPI server failure - store error, don't show immediately."""
        # Don't process if dialog is closing
        if self._is_closing:
            return
        
        # Don't store error if server is actually running (false alarm)
        if self.server_manager and self.server_manager.is_fastapi_running():
            logger.warning(f"FastAPI failed signal received but server is running: {msg}")
            self._fastapi_failure_msg = None  # Clear any previous failure
            return
        
        # Store failure message - will be shown when user tries to use servers
        self._fastapi_failure_msg = msg
        logger.warning(f"FastAPI server failure stored: {msg}")
        
        # If servers are no longer starting, we can reset the button
        if not self._servers_starting:
            self.submit_api_key_btn.setEnabled(True)
            self.submit_api_key_btn.setText("Submit API Key")
    
    def _on_mcp_failed(self, msg: str):
        """Handle MCP server failure - store error, don't show immediately."""
        # Don't process if dialog is closing
        if self._is_closing:
            return
        
        # Don't store error if server is actually running (false alarm)
        if self.server_manager and self.server_manager.is_mcp_running():
            logger.warning(f"MCP failed signal received but server is running: {msg}")
            self._mcp_failure_msg = None  # Clear any previous failure
            return
        
        # Store failure message - will be shown when user tries to use servers
        self._mcp_failure_msg = msg
        logger.warning(f"MCP server failure stored: {msg}")
        
        # If servers are no longer starting, we can reset the buttons
        if not self._servers_starting:
            self.submit_api_key_btn.setEnabled(True)
            self.submit_api_key_btn.setText("Submit API Key")
            self.stop_servers_btn.setEnabled(False)
            self.restart_servers_btn.setEnabled(True if self.api_key else False)
    
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
        
        # Display formatted SQL (but don't execute)
        formatted_sql = self._format_sql(self.current_sql)
        self.sql_display.setPlainText(formatted_sql)
        self.sql_display.setEnabled(True)
        
        # Enable execute button so user can run the query
        self.execute_sql_btn.setEnabled(True)
        
        # Cache the query (non-blocking, with error handling)
        if sql_query and sql_query.strip() and self.query_cache is not None:
            try:
                cache_id = self.query_cache.add_query(
                    nl_query=self.nl_query_input.toPlainText().strip(),
                    sql_query=self.current_sql,
                    formatted_sql=formatted_sql
                )
                # Defer dropdown refresh to avoid blocking UI
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self._refresh_cache_dropdown)
            except Exception as e:
                logger.warning(f"Failed to cache query: {e}", exc_info=True)
                # Continue without caching - don't block user
        
        # Clear previous results
        self.results_table.setModel(None)
        self.query_results = None
        self.query_results_df = None
        self._original_dataframe = None
    
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
            self.stats_btn.setEnabled(False)
            self.filter_btn.setEnabled(False)
            self.reset_filter_btn.setEnabled(False)
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
        
        # Enable table and analysis buttons
        self.results_table.setEnabled(True)
        self.stats_btn.setEnabled(True)
        self.filter_btn.setEnabled(True)
        # Enable reset filter only if we have an original dataframe and it's different
        if self._original_dataframe is not None and not df.equals(self._original_dataframe):
            self.reset_filter_btn.setEnabled(True)
        else:
            self.reset_filter_btn.setEnabled(False)
    
    def _show_dataframe_stats(self):
        """Display DataFrame statistics in a dialog."""
        if self.query_results_df is None or self.query_results_df.empty:
            QMessageBox.warning(self, "No Data", "No data available for statistics.")
            return
        
        df = self.query_results_df
        
        # Create statistics text
        stats_text = []
        stats_text.append("=== DataFrame Statistics ===\n")
        stats_text.append(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns\n")
        stats_text.append(f"Memory Usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB\n\n")
        
        # Column info
        stats_text.append("=== Column Information ===\n")
        for col in df.columns:
            dtype = df[col].dtype
            null_count = df[col].isna().sum()
            null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
            stats_text.append(f"{col} ({dtype}): {null_count} nulls ({null_pct:.1f}%)\n")
        
        # Numeric statistics
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            stats_text.append("\n=== Numeric Statistics ===\n")
            try:
                stats_text.append(df[numeric_cols].describe().to_string())
            except Exception as e:
                stats_text.append(f"Error generating statistics: {str(e)}")
        
        # Show in dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("DataFrame Statistics")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText("".join(stats_text))
        text_edit.setFontFamily("Courier")
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        
        layout.addWidget(text_edit)
        layout.addWidget(close_btn)
        dialog.setLayout(layout)
        dialog.exec()
    
    def _show_filter_dialog(self):
        """Show dialog to filter DataFrame by column conditions."""
        if self.query_results_df is None or self.query_results_df.empty:
            QMessageBox.warning(self, "No Data", "No data available to filter.")
            return
        
        df = self.query_results_df
        
        # Simple filter dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Filter Data")
        dialog.setMinimumSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Column selection
        col_label = QLabel("Column:")
        col_combo = QComboBox()
        col_combo.addItems([str(col) for col in df.columns])
        layout.addWidget(col_label)
        layout.addWidget(col_combo)
        
        # Filter condition
        condition_label = QLabel("Condition (e.g., > 100, == 'value', contains 'text'):")
        condition_input = QLineEdit()
        condition_input.setPlaceholderText("Enter filter condition...")
        layout.addWidget(condition_label)
        layout.addWidget(condition_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply Filter")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        def apply_filter():
            column = col_combo.currentText()
            condition = condition_input.text().strip()
            
            if not condition:
                QMessageBox.warning(dialog, "Invalid Filter", "Please enter a filter condition.")
                return
            
            try:
                # Try to use pandas query() for filtering
                # Support common conditions: >, <, >=, <=, ==, !=, contains
                query_str = f"{column} {condition}"
                filtered_df = df.query(query_str)
                
                if filtered_df.empty:
                    QMessageBox.information(dialog, "No Results", 
                                          "Filter returned no results.")
                    return
                
                # Update displayed DataFrame
                self.query_results_df = filtered_df
                self._display_dataframe(filtered_df)
                dialog.close()
                
            except Exception as e:
                # If query() fails, try eval() as fallback (less safe but more flexible)
                try:
                    # Create a safe evaluation context
                    safe_dict = {col: df[col] for col in df.columns}
                    # Try to evaluate condition
                    if condition.startswith('>') or condition.startswith('<') or \
                       condition.startswith('>=') or condition.startswith('<=') or \
                       condition.startswith('==') or condition.startswith('!='):
                        # Simple comparison
                        filtered_df = df[eval(f"df['{column}'] {condition}")]
                    elif 'contains' in condition.lower():
                        # String contains
                        search_term = condition.split("'")[1] if "'" in condition else condition.split('"')[1]
                        filtered_df = df[df[column].astype(str).str.contains(search_term, case=False, na=False)]
                    else:
                        raise ValueError("Unsupported filter condition")
                    
                    if filtered_df.empty:
                        QMessageBox.information(dialog, "No Results", 
                                              "Filter returned no results.")
                        return
                    
                    self.query_results_df = filtered_df
                    self._display_dataframe(filtered_df)
                    dialog.close()
                    
                except Exception as e2:
                    QMessageBox.critical(dialog, "Filter Error", 
                                       f"Failed to apply filter: {str(e2)}\n\n"
                                       f"Supported formats:\n"
                                       f"- Comparison: > 100, < 50, >= 10, <= 20, == 'value', != 'value'\n"
                                       f"- Contains: contains 'text'")
        
        apply_btn.clicked.connect(apply_filter)
        cancel_btn.clicked.connect(dialog.close)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _reset_filter(self):
        """Reset filter and show original DataFrame."""
        if self._original_dataframe is None:
            return
        
        # Restore original DataFrame
        self.query_results_df = self._original_dataframe.copy()
        self._display_dataframe(self.query_results_df)
    
    def _refresh_cache_dropdown(self):
        """Refresh the cached queries dropdown with current cache."""
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
            if hasattr(self, 'execute_cached_btn'):
                self.execute_cached_btn.setEnabled(False)
            return
        
        # Add cached queries to dropdown
        for query in cached_queries:
            display_text = f"{query['display_name']} ({self._format_timestamp(query['timestamp'])})"
            self.query_cache_combo.addItem(display_text, query['id'])
            # Add tooltip with full NL query
            item_index = self.query_cache_combo.count() - 1
            self.query_cache_combo.setItemData(item_index, query['nl_query'], Qt.ToolTipRole)
        
        # Always enable dropdown (no API key required)
        self.query_cache_combo.setEnabled(True)
        if hasattr(self, 'clear_cache_btn'):
            self.clear_cache_btn.setEnabled(True)
        if hasattr(self, 'execute_cached_btn'):
            # Only enable if a query is selected
            self.execute_cached_btn.setEnabled(False)  # Will be enabled on selection
        
        # Add placeholder option at top
        self.query_cache_combo.insertItem(0, "Select a cached query...", None)
        self.query_cache_combo.setCurrentIndex(0)
    
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
            # Placeholder selected, clear SQL display
            self.sql_display.clear()
            self.current_sql = None
            self.execute_sql_btn.setEnabled(False)  # For new queries (needs API key)
            self.execute_cached_btn.setEnabled(False)  # For cached queries
            self.results_table.setModel(None)
            self.results_status_label.setText("Select a cached query to view or execute...")
            self.results_status_label.setVisible(True)
            return
        
        if self.query_cache is None:
            QMessageBox.warning(self, "Cache Unavailable", "Query cache is not available.")
            return
        
        cached_query = self.query_cache.get_query(cache_id)
        if not cached_query:
            QMessageBox.warning(self, "Cache Error", "Selected query not found in cache.")
            return
        
        # Populate SQL display with cached formatted SQL (right below dropdown in right panel)
        self.sql_display.setPlainText(cached_query["formatted_sql"])
        self.sql_display.setEnabled(True)  # Enable for viewing/editing
        self.current_sql = cached_query["sql_query"]  # Store raw SQL for execution
        
        # Enable execute button for cached query (no API key required)
        self.execute_cached_btn.setEnabled(True)
        self.execute_cached_btn.setText("Execute Cached Query")
        
        # Keep execute_sql_btn disabled if no API key (for new queries)
        # Only enable if API key is set
        if self.api_key:
            self.execute_sql_btn.setEnabled(True)
        else:
            self.execute_sql_btn.setEnabled(False)
        
        # Clear previous results
        self.results_table.setModel(None)
        self.results_status_label.setText("Cached query loaded. Click 'Execute Cached Query' to run it (no API key needed).")
        self.results_status_label.setVisible(True)
    
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
    
    def _handle_execute_cached_query(self):
        """Handle execution of cached query - works without API key."""
        if not self.current_sql:
            QMessageBox.warning(self, "No SQL Query", "No cached query selected to execute.")
            return
        
        # Check if MCP server is running (needed for execution)
        if not self.server_manager or not self.server_manager.is_mcp_running():
            # Try to start MCP server (doesn't require API key)
            if not self.server_manager:
                self.server_manager = NLServerManager(parent=self)
                self.server_manager.mcp_failed.connect(self._on_mcp_failed)
            
            # Start only MCP server (no API key needed)
            self.server_manager.start_mcp_server(
                output_callback=self._on_mcp_output,
                error_callback=self._on_mcp_error
            )
            
            # Wait for server to start (or show message)
            QMessageBox.information(
                self, 
                "Starting Server", 
                "Starting MCP server for query execution. Please wait..."
            )
            # Note: In production, use signals to detect when server is ready
            return
        
        # Execute the cached SQL query
        self.execute_cached_btn.setEnabled(False)
        self.execute_cached_btn.setText("Executing...")
        
        # Use existing SQLExecuteThread (works with MCP server only)
        self.execute_thread = SQLExecuteThread(self.current_sql, "http://localhost:8001")
        self.execute_thread.finished.connect(self._on_execution_complete)
        self.execute_thread.start()
        
        # Update status
        self.results_status_label.setText("Executing cached query...")
        self.results_status_label.setVisible(True)
    
    def _on_search_filter_changed(self, text: str):
        """Filter cached queries based on search text."""
        search_text = text.strip().lower()
        
        if not search_text:
            # Show all queries
            self._refresh_cache_dropdown()
            return
        
        # Get all cached queries
        if self.query_cache is None:
            self.query_cache_combo.clear()
            self.query_cache_combo.addItem("Cache unavailable", None)
            self.query_cache_combo.setEnabled(False)
            return
        
        try:
            all_queries = self.query_cache.get_all_queries()
        except Exception as e:
            logger.warning(f"Failed to get cached queries for search: {e}", exc_info=True)
            self.query_cache_combo.clear()
            self.query_cache_combo.addItem("Error loading cache", None)
            self.query_cache_combo.setEnabled(False)
            return
        
        # Filter queries that match search text
        filtered_queries = []
        for query in all_queries:
            # Search in NL query
            if search_text in query['nl_query'].lower():
                filtered_queries.append(query)
                continue
            # Search in SQL query
            if search_text in query['sql_query'].lower():
                filtered_queries.append(query)
                continue
            # Search in formatted SQL
            if search_text in query['formatted_sql'].lower():
                filtered_queries.append(query)
                continue
            # Search in display name
            if search_text in query['display_name'].lower():
                filtered_queries.append(query)
        
        # Update dropdown with filtered results
        self.query_cache_combo.clear()
        
        if not filtered_queries:
            self.query_cache_combo.addItem("No matching queries", None)
            self.query_cache_combo.setEnabled(True)
            if hasattr(self, 'execute_cached_btn'):
                self.execute_cached_btn.setEnabled(False)
            return
        
        # Add filtered queries to dropdown
        for query in filtered_queries:
            display_text = f"{query['display_name']} ({self._format_timestamp(query['timestamp'])})"
            self.query_cache_combo.addItem(display_text, query['id'])
        
        self.query_cache_combo.setEnabled(True)
        if hasattr(self, 'execute_cached_btn'):
            self.execute_cached_btn.setEnabled(False)  # Will be enabled on selection
        
        # Add placeholder option at top
        self.query_cache_combo.insertItem(0, "Select a cached query...", None)
        self.query_cache_combo.setCurrentIndex(0)
    
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
        
        # Create export directories if they don't exist
        formatted_dir = get_data_path("exports", "nl_queries", "formatted")
        results_dir = get_data_path("exports", "nl_queries", "results")
        formatted_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Export 1: Formatted SQL Query to formatted/ folder
            formatted_filename = f"formatted_query_{timestamp}.csv"
            formatted_path = formatted_dir / formatted_filename
            
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
            
            # Export 2: Query Results to results/ folder (if available)
            results_path = None
            if has_results:
                results_filename = f"query_results_{timestamp}.csv"
                results_path = results_dir / results_filename
                
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
            message = f"Export successful!\n\n"
            message += f"Formatted Query:\n{formatted_path}\n"
            message += f"Location: data/exports/nl_queries/formatted/\n\n"
            
            if results_path:
                message += f"Query Results:\n{results_path}\n"
                message += f"Location: data/exports/nl_queries/results/"
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
        default_dir = str(get_data_path("exports", "nl_queries", "formatted"))
        
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
    
    def _handle_execute_sql(self):
        """Handle SQL execution - runs query on database and displays results in bottom right."""
        if not self.current_sql:
            QMessageBox.warning(self, "No SQL Query", "No SQL query available to execute.")
            return
        
        # Disable button during execution
        self.execute_sql_btn.setEnabled(False)
        self.execute_sql_btn.setText("Executing...")
        self.results_table.setModel(None)
        self.results_status_label.setText("Executing query...")
        self.results_status_label.setVisible(True)
        
        # Start execution thread
        self.execute_thread = SQLExecuteThread(self.current_sql, "http://localhost:8001")
        self.execute_thread.finished.connect(self._on_execution_complete)
        self.execute_thread.start()
    
    def _on_execution_complete(self, results: Optional[list]):
        """Handle SQL execution completion."""
        self.execute_sql_btn.setEnabled(True)
        self.execute_sql_btn.setText("Execute SQL Query")
        
        # Reset execute button for cached queries
        if hasattr(self, 'execute_cached_btn'):
            self.execute_cached_btn.setEnabled(True)
            self.execute_cached_btn.setText("Execute Cached Query")
        
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
    
    def closeEvent(self, event: QCloseEvent):
        """Handle dialog close - keep servers running for persistence."""
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
        
        # IMPORTANT: Do NOT stop servers - keep them running for persistence
        # Servers will remain running via GlobalServerManager
        # This allows user to close dialog and reopen later without restarting servers
        logger.info("Dialog closing - servers will remain running for persistence")
        
        # Save API key if it was changed
        if self.api_key:
            self.api_key_manager.save_api_key(self.api_key)
        
        event.accept()
