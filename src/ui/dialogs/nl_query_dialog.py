"""
NL-to-SQL Query Dialog for natural language database queries.

Provides a GUI for natural language database queries using OpenAI and FastAPI.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMessageBox, QHeaderView
)
from PySide6.QtCore import QThread, Signal, Qt
from src.utils.nl_sql_server import NLServerManager
from typing import Optional
import os
import requests
import logging

logger = logging.getLogger(__name__)


class NLQueryThread(QThread):
    """Thread for sending NL query to FastAPI server."""
    
    finished = Signal(dict)  # Emits {'sql': str, 'results': list} or None
    
    def __init__(self, api_key: str, query: str, fastapi_url: str):
        super().__init__()
        self.api_key = api_key
        self.query = query
        self.fastapi_url = fastapi_url
    
    def run(self):
        """Send NL query and parse response."""
        try:
            response = requests.post(
                f"{self.fastapi_url}/mcp/ask",
                json={"question": self.query},
                headers={"Authorization": f"Bearer {self.api_key}"},
                stream=True,
                timeout=(10, 120)
            )
            
            if response.status_code != 200:
                logger.error(f"Query failed with status {response.status_code}")
                self.finished.emit(None)
                return
            
            # Parse streaming response
            full_response = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    full_response += line + "\n"
            
            # Check for errors
            if "ERROR:" in full_response:
                logger.error(f"Query error: {full_response}")
                self.finished.emit(None)
                return
            
            # Parse SQL and results
            separator = "\n\n---\n\nRESULTS:\n"
            if separator in full_response:
                parts = full_response.split(separator, 1)
                sql_query = parts[0].strip()
                results_part = parts[1] if len(parts) > 1 else ""
                
                # Parse results
                results = self._parse_results(results_part)
                self.finished.emit({"sql": sql_query, "results": results})
            else:
                logger.warning("Response missing separator, SQL only")
                # Try to extract SQL even without separator
                if full_response.strip():
                    self.finished.emit({"sql": full_response.strip(), "results": None})
                else:
                    self.finished.emit(None)
        except Exception as e:
            logger.error(f"Query thread error: {str(e)}", exc_info=True)
            self.finished.emit(None)
    
    def _parse_results(self, results_text: str):
        """Parse results from response text."""
        if not results_text or not results_text.strip():
            return []
        
        if "ERROR:" in results_text:
            return None
        
        lines = [line.strip() for line in results_text.strip().split("\n") if line.strip()]
        if not lines:
            return []
        
        headers = [h.strip() for h in lines[0].split("|")]
        data_lines = [line for line in lines[1:] if not all(c in "-| " for c in line)]
        
        if not data_lines:
            return []
        
        results = []
        for line in data_lines:
            values = [v.strip() for v in line.split("|")]
            row = {}
            for i, header in enumerate(headers):
                row[header] = values[i] if i < len(values) else ""
            results.append(row)
        
        return results


class NLQueryDialog(QDialog):
    """Dialog for NL-to-SQL queries."""
    
    # Signal emitted when query completes successfully
    query_completed = Signal(dict)  # {'sql': str, 'results': list}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NL-to-SQL Query")
        self.setMinimumSize(900, 650)
        
        # State
        self.api_key: Optional[str] = None
        self.server_manager: Optional[NLServerManager] = None
        self.query_thread: Optional[NLQueryThread] = None
        self.query_results: Optional[list] = None
        
        # Create UI
        self._create_ui()
        self._setup_initial_state()
    
    def _create_ui(self):
        """Create the two-panel UI layout."""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Left panel
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel
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
        """Create right panel with SQL display and execute button."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # SQL Display Section
        sql_label = QLabel("Generated SQL Query:")
        self.sql_display = QTextEdit()
        self.sql_display.setReadOnly(True)
        self.sql_display.setPlaceholderText("SQL query will appear here after submitting NL query...")
        self.sql_display.setMinimumHeight(200)
        
        self.execute_sql_btn = QPushButton("Execute SQL")
        self.execute_sql_btn.clicked.connect(self._handle_execute_sql)
        
        layout.addWidget(sql_label)
        layout.addWidget(self.sql_display)
        layout.addWidget(self.execute_sql_btn)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def _setup_initial_state(self):
        """Set initial widget states."""
        self.nl_query_input.setEnabled(False)
        self.submit_nl_query_btn.setEnabled(False)
        self.sql_display.setEnabled(False)
        self.execute_sql_btn.setEnabled(False)
    
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
        self.submit_api_key_btn.setEnabled(True)
        self.submit_api_key_btn.setText("Submit API Key")
        QMessageBox.critical(self, "Server Error", f"FastAPI server failed: {msg}")
    
    def _on_mcp_failed(self, msg: str):
        """Handle MCP server failure."""
        self.submit_api_key_btn.setEnabled(True)
        self.submit_api_key_btn.setText("Submit API Key")
        QMessageBox.critical(self, "Server Error", f"MCP server failed: {msg}")
    
    def _handle_nl_query_submit(self):
        """Handle NL query submission."""
        query = self.nl_query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "Empty Query", "Please enter a natural language query.")
            return
        
        self.submit_nl_query_btn.setEnabled(False)
        self.submit_nl_query_btn.setText("Processing...")
        self.sql_display.clear()
        self.sql_display.setPlainText("Generating SQL query...")
        
        # Start query thread
        self.query_thread = NLQueryThread(self.api_key, query, "http://localhost:8000")
        self.query_thread.finished.connect(self._on_query_complete)
        self.query_thread.start()
    
    def _on_query_complete(self, result: Optional[dict]):
        """Handle query completion."""
        self.submit_nl_query_btn.setEnabled(True)
        self.submit_nl_query_btn.setText("Submit NL Query")
        
        # Handle None result (error occurred)
        if result is None:
            QMessageBox.warning(self, "Query Failed", 
                              "Failed to generate SQL query. Please check your query and try again.\n\n"
                              "Common issues:\n"
                              "- Server may not be ready yet\n"
                              "- Invalid query format\n"
                              "- Network connection error")
            self.sql_display.clear()
            return
        
        # Handle missing SQL in result
        if not result.get("sql"):
            QMessageBox.warning(self, "Query Failed", 
                              "Failed to generate SQL query. Please check your query and try again.")
            self.sql_display.clear()
            return
        
        # Display formatted SQL
        formatted_sql = self._format_sql(result["sql"])
        self.sql_display.setPlainText(formatted_sql)
        self.sql_display.setEnabled(True)
        
        # Store results for execution
        self.query_results = result.get("results")
        
        # Enable execute button
        self.execute_sql_btn.setEnabled(True)
        
        # Emit signal for integration with search dialog (optional)
        self.query_completed.emit(result)
    
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
        """Handle SQL execution and show results."""
        if self.query_results is None:
            QMessageBox.warning(self, "No Results", "No query results available to display.")
            return
        
        if not self.query_results:
            QMessageBox.information(self, "No Results", "Query returned no results.")
            return
        
        # Show results dialog
        self._show_results_dialog(self.query_results)
    
    def _show_results_dialog(self, results: list):
        """Show results in a new dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Query Results")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Results table
        tree = QTreeWidget()
        tree.setHeaderLabels(list(results[0].keys()) if results else [])
        tree.setAlternatingRowColors(True)
        tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        for row in results:
            item = QTreeWidgetItem()
            for i, (key, value) in enumerate(row.items()):
                item.setText(i, str(value))
            tree.addTopLevelItem(item)
        
        layout.addWidget(QLabel(f"Total rows: {len(results)}"))
        layout.addWidget(tree)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def closeEvent(self, event):
        """Stop servers when dialog closes."""
        if self.server_manager:
            self.server_manager.stop_all_servers()
        event.accept()
