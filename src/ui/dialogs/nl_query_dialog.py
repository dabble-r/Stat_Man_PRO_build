"""
NL-to-SQL Query Dialog for natural language database queries.

Provides a GUI for natural language database queries using OpenAI and FastAPI.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMessageBox, QHeaderView, QSplitter
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QCloseEvent
from src.utils.nl_sql_server import NLServerManager
from typing import Optional
import os
import requests
import logging

logger = logging.getLogger(__name__)


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
        self.query_results: Optional[list] = None
        self._is_closing = False  # Flag to prevent error messages during close
        
        # Create UI
        self._create_ui()
        self._setup_initial_state()
    
    def _create_ui(self):
        """Create the UI layout with left panel (inputs) and right panel (SQL + results)."""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Left panel (inputs)
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel (SQL display + results)
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, stretch=1)
        
        self.setLayout(main_layout)
    
    def _create_left_panel(self) -> QWidget:
        """Create left panel with API key and NL query inputs."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # API Key Section
        api_key_label = QLabel("OpenAI API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key...")
        
        self.submit_api_key_btn = QPushButton("Submit API Key")
        self.submit_api_key_btn.clicked.connect(self._handle_api_key_submit)
        
        layout.addWidget(api_key_label)
        layout.addWidget(self.api_key_input)
        layout.addWidget(self.submit_api_key_btn)
        
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
        """Create right panel with SQL display, execute button, and results."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # SQL Display Section (top)
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
        self.results_tree = QTreeWidget()
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setHeaderHidden(False)
        self.results_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_tree.setMinimumHeight(250)
        # QTreeWidget doesn't have setPlaceholderText, so we'll show a message via label
        self.results_status_label = QLabel("Results will appear here after executing SQL query...")
        self.results_status_label.setAlignment(Qt.AlignCenter)
        self.results_status_label.setStyleSheet("color: gray; font-style: italic;")
        
        layout.addWidget(results_label)
        layout.addWidget(self.results_status_label)
        layout.addWidget(self.results_tree)
        
        panel.setLayout(layout)
        return panel
    
    def _setup_initial_state(self):
        """Set initial widget states."""
        self.nl_query_input.setEnabled(False)
        self.submit_nl_query_btn.setEnabled(False)
        self.sql_display.setEnabled(False)
        self.execute_sql_btn.setEnabled(False)
        self.results_tree.setEnabled(False)
    
    def _validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format."""
        if not api_key or len(api_key) < 20:
            return False
        return api_key.startswith("sk-") or len(api_key) > 40
    
    def _handle_api_key_submit(self):
        """Handle API key submission and start servers."""
        api_key = self.api_key_input.text().strip()
        
        if not self._validate_api_key_format(api_key):
            QMessageBox.warning(self, "Invalid API Key", 
                              "API key must start with 'sk-' or be at least 40 characters long.")
            return
        
        self.api_key = api_key
        self.submit_api_key_btn.setEnabled(False)
        self.submit_api_key_btn.setText("Starting Servers...")
        
        # Start servers
        self._start_servers()
    
    def _start_servers(self):
        """Start both FastAPI and MCP servers."""
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
        self.submit_api_key_btn.setText("API Key Validated ✓")
        self.submit_api_key_btn.setEnabled(False)
        
        # Mask API key
        masked = self.api_key[:7] + "*" * (len(self.api_key) - 11) + self.api_key[-4:]
        self.api_key_input.setText(masked)
        self.api_key_input.setReadOnly(True)
        
        # Enable NL query section
        self.nl_query_input.setEnabled(True)
        self.submit_nl_query_btn.setEnabled(True)
        
        QMessageBox.information(self, "Servers Ready", 
                              "Both servers are ready. You can now submit queries.")
    
    def _on_fastapi_ready(self):
        """Handle FastAPI server ready signal."""
        # Individual server ready - all_servers_ready will be called when both are ready
        pass
    
    def _on_mcp_ready(self):
        """Handle MCP server ready signal."""
        # Individual server ready - all_servers_ready will be called when both are ready
        pass
    
    def _on_fastapi_failed(self, msg: str):
        """Handle FastAPI server failure."""
        # Don't show error messages if dialog is closing
        if self._is_closing:
            return
        
        self.submit_api_key_btn.setEnabled(True)
        self.submit_api_key_btn.setText("Submit API Key")
        QMessageBox.critical(self, "Server Error", f"FastAPI server failed: {msg}")
    
    def _on_mcp_failed(self, msg: str):
        """Handle MCP server failure."""
        # Don't show error messages if dialog is closing
        if self._is_closing:
            return
        
        self.submit_api_key_btn.setEnabled(True)
        self.submit_api_key_btn.setText("Submit API Key")
        QMessageBox.critical(self, "Server Error", f"MCP server failed: {msg}")
    
    def _handle_nl_query_submit(self):
        """Handle NL query submission - only generates SQL, doesn't execute."""
        query = self.nl_query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "Empty Query", "Please enter a natural language query.")
            return
        
        self.submit_nl_query_btn.setEnabled(False)
        self.submit_nl_query_btn.setText("Processing...")
        self.sql_display.clear()
        self.sql_display.setPlainText("Generating SQL query...")
        self.execute_sql_btn.setEnabled(False)
        self.results_tree.clear()
        
        # Start query thread (only gets SQL, doesn't execute)
        self.query_thread = NLQueryThread(self.api_key, query, "http://localhost:8000")
        self.query_thread.finished.connect(self._on_query_complete)
        self.query_thread.start()
    
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
        
        # Clear previous results
        self.results_tree.clear()
        self.query_results = None
    
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
    
    def _handle_execute_sql(self):
        """Handle SQL execution - runs query on database and displays results in bottom right."""
        if not self.current_sql:
            QMessageBox.warning(self, "No SQL Query", "No SQL query available to execute.")
            return
        
        # Disable button during execution
        self.execute_sql_btn.setEnabled(False)
        self.execute_sql_btn.setText("Executing...")
        self.results_tree.clear()
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
        
        if results is None:
            QMessageBox.warning(self, "Execution Failed", 
                              "Failed to execute SQL query. Please check the query and try again.")
            self.results_status_label.setText("Execution failed. Please try again.")
            self.results_status_label.setVisible(True)
            return
        
        # Store results
        self.query_results = results
        
        # Display results in bottom right tree widget
        if not results:
            self.results_status_label.setText("Query returned no results.")
            self.results_status_label.setVisible(True)
            QMessageBox.information(self, "No Results", "Query returned no results.")
            return
        
        # Set up tree widget with headers
        headers = list(results[0].keys()) if results else []
        self.results_tree.setHeaderLabels(headers)
        self.results_tree.setEnabled(True)
        
        # Populate tree with results
        for row in results:
            item = QTreeWidgetItem()
            for i, (key, value) in enumerate(row.items()):
                item.setText(i, str(value) if value is not None else "")
            self.results_tree.addTopLevelItem(item)
        
        # Update status label to show row count and hide it
        self.results_status_label.setText(f"Total rows: {len(results)}")
        self.results_status_label.setVisible(False)  # Hide when results are shown
    
    def closeEvent(self, event: QCloseEvent):
        """Stop servers when dialog closes."""
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
        
        # Stop servers (this may trigger process termination, but we've disconnected error handlers)
        if self.server_manager:
            self.server_manager.stop_all_servers()
        
        event.accept()
