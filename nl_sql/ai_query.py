import sqlite3
import json
import requests
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import path resolver to get database path
from src.utils.path_resolver import get_database_path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QProcess, QTimer
from src.ui.styles.stylesheets import StyleSheets


class MCPRequestThread(QThread):
    """Thread for making async MCP server requests to avoid blocking GUI."""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, mcp_url: str, payload: dict):
        super().__init__()
        self.mcp_url = mcp_url
        self.payload = payload
    
    def run(self):
        """Execute the MCP server request."""
        try:
            response = requests.post(self.mcp_url, json=self.payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.finished.emit(data)
        except requests.exceptions.ConnectionError as e:
            # More helpful error message for connection refused
            error_msg = str(e)
            if "Connection refused" in error_msg or "Failed to establish" in error_msg:
                self.error.emit("Server not running: Connection refused. Please start the FastAPI server.")
            else:
                self.error.emit(f"Connection error: {str(e)}")
        except requests.exceptions.Timeout as e:
            self.error.emit(f"Request timeout: Server took too long to respond. {str(e)}")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
            self.error.emit(f"HTTP error {status_code}: {str(e)}")
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            self.error.emit(f"Invalid response format: {str(e)}")
        except Exception as e:
            self.error.emit(f"Unexpected error: {str(e)}")


class LLMtoSQLiteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM → MCP → SQLite Assistant")
        self.resize(800, 600)
        self.setStyleSheet(StyleSheets().get_monochrome_1_style())

        layout = QVBoxLayout()

        # --- MCP Server URL with Status ---
        server_row = QHBoxLayout()
        server_row.addWidget(QLabel("MCP Server URL:"))
        self.server_url_input = QLineEdit()
        self.server_url_input.setText("http://localhost:8000")
        self.server_url_input.setPlaceholderText("http://localhost:8000")
        server_row.addWidget(self.server_url_input)
        
        # Server status indicator
        self.server_status_label = QLabel("●")
        self.server_status_label.setStyleSheet("color: gray; font-size: 16px;")
        self.server_status_label.setToolTip("Server status: Unknown")
        server_row.addWidget(self.server_status_label)
        
        # Check server button
        self.check_server_btn = QPushButton("Check")
        self.check_server_btn.setMaximumWidth(60)
        self.check_server_btn.clicked.connect(self.check_server_status)
        server_row.addWidget(self.check_server_btn)
        
        layout.addLayout(server_row)

        # --- LLM Provider Info (OpenAI only) ---
        llm_row = QHBoxLayout()
        llm_row.addWidget(QLabel("LLM Provider:"))
        llm_label = QLabel("OpenAI")
        llm_label.setStyleSheet("color: #666666; font-style: italic;")
        llm_row.addWidget(llm_label)
        llm_row.addStretch()
        layout.addLayout(llm_row)

        # --- API Key ---
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter OpenAI API key (server will auto-start)")
        # Connect signal to auto-start server when API key is entered
        self.api_key_input.editingFinished.connect(self._on_api_key_entered)
        key_row.addWidget(self.api_key_input)
        layout.addLayout(key_row)

        # --- User Natural Language Request ---
        layout.addWidget(QLabel("Describe the data you want:"))
        self.user_request = QTextEdit()
        layout.addWidget(self.user_request)

        # --- Database Info (read-only display) ---
        db_info_row = QHBoxLayout()
        db_info_row.addWidget(QLabel("Database:"))
        # Get database path using project's path resolver
        try:
            db_path = get_database_path()
            self.database_path = db_path
            # Extract database name from path (e.g., "League" from "League.db")
            db_name = db_path.stem if db_path.suffix == '.db' else 'League'
            self.database_name = db_name.lower()  # Use lowercase for MCP server identifier
        except Exception:
            # Fallback to default
            self.database_path = project_root / "data" / "database" / "League.db"
            self.database_name = "league"
        
        db_info_label = QLabel(f"{self.database_name} ({self.database_path.name})")
        db_info_label.setStyleSheet("color: #666666; font-style: italic;")
        db_info_label.setToolTip(f"Database: {self.database_name}\nPath: {self.database_path}")
        db_info_row.addWidget(db_info_label)
        db_info_row.addStretch()
        layout.addLayout(db_info_row)

        # --- Button: Send to MCP Server ---
        self.refactor_btn = QPushButton("Refactor to SQLite Query")
        self.refactor_btn.clicked.connect(self.refactor_to_sql)
        layout.addWidget(self.refactor_btn)

        # --- Display Schema Context (collapsible) ---
        schema_label = QLabel("Schema Context (from MCP server):")
        layout.addWidget(schema_label)
        self.schema_output = QTextEdit()
        self.schema_output.setReadOnly(True)
        self.schema_output.setMaximumHeight(150)
        self.schema_output.setPlaceholderText("Schema context will appear here after query generation...")
        layout.addWidget(self.schema_output)

        # --- Display Generated SQL ---
        layout.addWidget(QLabel("Generated SQLite Query:"))
        self.sql_output = QTextEdit()
        self.sql_output.setReadOnly(True)
        layout.addWidget(self.sql_output)
        
        # --- Validation Status ---
        validation_row = QHBoxLayout()
        validation_row.addWidget(QLabel("Validation:"))
        self.validation_label = QLabel("Not validated")
        self.validation_label.setStyleSheet("color: gray;")
        validation_row.addWidget(self.validation_label)
        validation_row.addStretch()
        layout.addLayout(validation_row)

        # --- Button: Run Query ---
        self.run_btn = QPushButton("Run Query")
        self.run_btn.clicked.connect(self.run_sql_query)
        layout.addWidget(self.run_btn)

        # --- Results Table ---
        layout.addWidget(QLabel("Query Results:"))
        self.results_table = QTableWidget()
        layout.addWidget(self.results_table)

        self.setLayout(layout)
        
        # Thread for async MCP requests
        self.mcp_thread: Optional[MCPRequestThread] = None
        
        # Server process management
        self.server_process: Optional[QProcess] = None
        self.server_starting = False
        
        # MCP server process management
        self.mcp_server_process: Optional[QProcess] = None
        self.mcp_server_starting = False
        
        # Check server status on startup
        self.check_server_status()

    # ---------------------------------------------------------
    # Server Management
    # ---------------------------------------------------------
    def _on_api_key_entered(self):
        """Called when user finishes entering API key - auto-start servers if needed."""
        api_key = self.api_key_input.text().strip()
        if api_key and not self.server_starting:
            # Check if servers are already running
            self.check_server_status()
            # Small delay to let status check complete, then check again
            QTimer.singleShot(500, self._auto_start_servers_if_needed)
    
    def _auto_start_servers_if_needed(self):
        """Auto-start servers (FastAPI and MCP) if API key is entered and servers are not running."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            return
        
        # Check FastAPI server status
        server_url = self.server_url_input.text().strip()
        try:
            response = requests.get(f"{server_url.rstrip('/')}/docs", timeout=1)
            if response.status_code != 200:
                # Server is not running, start it
                self.start_server_automatically()
        except:
            # Server is not running, start it
            self.start_server_automatically()
        
        # Check MCP server status and start if needed
        self._check_and_start_mcp_server()
    
    def start_server_automatically(self):
        """Start the FastAPI server automatically in the background."""
        if self.server_process and self.server_process.state() == QProcess.ProcessState.Running:
            # Server already running
            return
        
        if self.server_starting:
            # Already starting
            return
        
        self.server_starting = True
        self.server_status_label.setText("●")
        self.server_status_label.setStyleSheet("color: orange; font-size: 16px;")
        self.server_status_label.setToolTip("Server status: Starting...")
        
        # Get the demo directory path
        demo_dir = Path(__file__).parent
        
        # Create QProcess to run server
        self.server_process = QProcess(self)
        self.server_process.setWorkingDirectory(str(demo_dir))
        
        # Connect signals
        self.server_process.readyReadStandardOutput.connect(self._on_server_output)
        self.server_process.readyReadStandardError.connect(self._on_server_error)
        self.server_process.finished.connect(self._on_server_finished)
        self.server_process.started.connect(self._on_server_started)
        
        # Start the server
        # Use Python to run start_server.py or uvicorn directly
        python_exe = sys.executable
        server_script = demo_dir / "start_server.py"
        
        # Set environment to ensure proper Python path
        env = self.server_process.processEnvironment()
        env.insert("PYTHONPATH", str(demo_dir))
        self.server_process.setProcessEnvironment(env)
        
        if server_script.exists():
            # Use the startup script
            print(f"[Server] Starting server with: {python_exe} {server_script}")
            success = self.server_process.start(python_exe, [str(server_script)])
        else:
            # Fallback: use uvicorn directly
            print(f"[Server] Starting server with uvicorn directly")
            success = self.server_process.start(
                python_exe,
                ["-m", "uvicorn", "api_call:app", "--host", "0.0.0.0", "--port", "8000"]
            )
        
        if not success:
            self.server_starting = False
            error_msg = self.server_process.errorString()
            self._update_server_status(False, f"Failed to start process: {error_msg}")
            QMessageBox.critical(
                self,
                "Server Start Failed",
                f"Failed to start server process:\n\n{error_msg}\n\n"
                "Make sure Python and required packages are installed."
            )
            return
        
        # Wait a moment for server to start, then check status
        QTimer.singleShot(3000, self._verify_server_started)
    
    def _on_server_started(self):
        """Called when server process starts."""
        self.server_status_label.setToolTip("Server status: Starting...")
    
    def _on_server_output(self):
        """Handle server stdout output."""
        output = bytes(self.server_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        # Print to console for debugging (can be removed later)
        print(f"[Server Output] {output.strip()}")
        
        # Look for startup confirmation messages
        if any(phrase in output for phrase in [
            "Application startup complete",
            "Uvicorn running",
            "Started server process",
            "Waiting for application startup"
        ]):
            # Server is starting up
            QTimer.singleShot(2000, self._verify_server_started)
    
    def _on_server_error(self):
        """Handle server stderr output."""
        error = bytes(self.server_process.readAllStandardError()).decode('utf-8', errors='ignore')
        # Print to console for debugging
        print(f"[Server Error] {error.strip()}")
        
        # Check for specific errors
        error_lower = error.lower()
        if "module not found" in error_lower or "no module named" in error_lower:
            # Missing dependencies
            self.server_starting = False
            self._update_server_status(False, "Missing dependencies - check console")
            QMessageBox.critical(
                self,
                "Server Startup Failed",
                f"Server failed to start due to missing dependencies:\n\n{error}\n\n"
                "Install required packages with:\n"
                "  pip install fastapi uvicorn openai"
            )
        elif "address already in use" in error_lower or "port 8000" in error_lower:
            # Port already in use - server might already be running
            QTimer.singleShot(1000, self._verify_server_started)
        elif "error" in error_lower:
            # Other errors - still check if server started
            QTimer.singleShot(2000, self._verify_server_started)
    
    def _on_server_finished(self, exit_code, exit_status):
        """Called when server process finishes."""
        self.server_starting = False
        if exit_code != 0:
            self._update_server_status(False, f"Server exited with code {exit_code}")
            # Read any remaining error output
            error_output = bytes(self.server_process.readAllStandardError()).decode('utf-8', errors='ignore')
            if error_output:
                print(f"[Server Exit Error] {error_output}")
            self.server_process = None
    
    def _verify_server_started(self):
        """Verify that the server actually started and is responding."""
        self.server_starting = False
        # Check server status
        self.check_server_status()
    
    def check_server_status(self):
        """Check if the FastAPI server is running."""
        server_url = self.server_url_input.text().strip()
        if not server_url:
            self._update_server_status(False, "No URL specified")
            return
        
        # Try to connect to the server
        try:
            # Try to access the docs endpoint (lightweight check)
            response = requests.get(f"{server_url.rstrip('/')}/docs", timeout=2)
            if response.status_code == 200:
                self._update_server_status(True, "Server is running")
            else:
                self._update_server_status(False, f"Server returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            self._update_server_status(False, "Server not running")
        except requests.exceptions.Timeout:
            self._update_server_status(False, "Server timeout")
        except Exception as e:
            self._update_server_status(False, f"Error: {str(e)}")
    
    def _update_server_status(self, is_online: bool, message: str):
        """Update server status indicator."""
        if is_online:
            self.server_status_label.setText("●")
            self.server_status_label.setStyleSheet("color: green; font-size: 16px;")
            self.server_status_label.setToolTip(f"Server status: {message}")
        else:
            self.server_status_label.setText("●")
            self.server_status_label.setStyleSheet("color: red; font-size: 16px;")
            self.server_status_label.setToolTip(f"Server status: {message}")
    
    # ---------------------------------------------------------
    # MCP Server Management
    # ---------------------------------------------------------
    def _check_and_start_mcp_server(self):
        """Check if MCP server is running, start if not."""
        if self.mcp_server_starting:
            return
        
        # Check if MCP server is already running
        try:
            response = requests.get("http://localhost:8001/health", timeout=1)
            if response.status_code == 200:
                # MCP server is running
                return
        except:
            # MCP server is not running, start it
            self.start_mcp_server_automatically()
    
    def start_mcp_server_automatically(self):
        """Start the MCP server automatically in the background."""
        if self.mcp_server_process and self.mcp_server_process.state() == QProcess.ProcessState.Running:
            # MCP server already running
            return
        
        if self.mcp_server_starting:
            # Already starting
            return
        
        self.mcp_server_starting = True
        print("[MCP Server] Starting MCP server...")
        
        # Get the demo directory path
        demo_dir = Path(__file__).parent
        
        # Create QProcess to run MCP server
        self.mcp_server_process = QProcess(self)
        self.mcp_server_process.setWorkingDirectory(str(demo_dir))
        
        # Connect signals
        self.mcp_server_process.readyReadStandardOutput.connect(self._on_mcp_server_output)
        self.mcp_server_process.readyReadStandardError.connect(self._on_mcp_server_error)
        self.mcp_server_process.finished.connect(self._on_mcp_server_finished)
        self.mcp_server_process.started.connect(self._on_mcp_server_started)
        
        # Start the MCP server
        python_exe = sys.executable
        mcp_server_script = demo_dir / "start_mcp_server.py"
        
        # Set environment to ensure proper Python path
        env = self.mcp_server_process.processEnvironment()
        env.insert("PYTHONPATH", str(demo_dir))
        self.mcp_server_process.setProcessEnvironment(env)
        
        if mcp_server_script.exists():
            # Use the startup script
            print(f"[MCP Server] Starting MCP server with: {python_exe} {mcp_server_script}")
            success = self.mcp_server_process.start(python_exe, [str(mcp_server_script)])
        else:
            # Fallback: use uvicorn directly
            print(f"[MCP Server] Starting MCP server with uvicorn directly")
            success = self.mcp_server_process.start(
                python_exe,
                ["-m", "uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8001"]
            )
        
        if not success:
            self.mcp_server_starting = False
            error_msg = self.mcp_server_process.errorString()
            print(f"[MCP Server] Failed to start: {error_msg}")
            return
        
        # Wait a moment for server to start, then verify
        QTimer.singleShot(3000, self._verify_mcp_server_started)
    
    def _on_mcp_server_started(self):
        """Called when MCP server process starts."""
        print("[MCP Server] Process started")
    
    def _on_mcp_server_output(self):
        """Handle MCP server stdout output."""
        output = bytes(self.mcp_server_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        print(f"[MCP Server Output] {output.strip()}")
        
        # Look for startup confirmation messages
        if any(phrase in output for phrase in [
            "Application startup complete",
            "Uvicorn running",
            "Started server process",
            "Waiting for application startup"
        ]):
            # Server is starting up
            QTimer.singleShot(2000, self._verify_mcp_server_started)
    
    def _on_mcp_server_error(self):
        """Handle MCP server stderr output."""
        error = bytes(self.mcp_server_process.readAllStandardError()).decode('utf-8', errors='ignore')
        print(f"[MCP Server Error] {error.strip()}")
        
        # Check for specific errors
        error_lower = error.lower()
        if "module not found" in error_lower or "no module named" in error_lower:
            # Missing dependencies
            self.mcp_server_starting = False
            print(f"[MCP Server] Missing dependencies - check console")
        elif "address already in use" in error_lower or "port 8001" in error_lower:
            # Port already in use - server might already be running
            QTimer.singleShot(1000, self._verify_mcp_server_started)
        elif "error" in error_lower:
            # Other errors - still check if server started
            QTimer.singleShot(2000, self._verify_mcp_server_started)
    
    def _on_mcp_server_finished(self, exit_code, exit_status):
        """Called when MCP server process finishes."""
        self.mcp_server_starting = False
        if exit_code != 0:
            error_output = bytes(self.mcp_server_process.readAllStandardError()).decode('utf-8', errors='ignore')
            if error_output:
                print(f"[MCP Server Exit Error] {error_output}")
            self.mcp_server_process = None
    
    def _verify_mcp_server_started(self):
        """Verify that the MCP server has actually started and is responding."""
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("[MCP Server] Verified: Server is running")
                self.mcp_server_starting = False
            else:
                # Server might still be starting, check again in a moment
                if self.mcp_server_starting:
                    QTimer.singleShot(2000, self._verify_mcp_server_started)
        except Exception as e:
            # Server might still be starting, check again in a moment
            if self.mcp_server_starting:
                QTimer.singleShot(2000, self._verify_mcp_server_started)
            else:
                print(f"[MCP Server] Not responding: {str(e)}")
    
    # ---------------------------------------------------------
    # STEP 1: Send natural-language request to MCP server
    # ---------------------------------------------------------
    def refactor_to_sql(self):
        # OpenAI is the only supported provider
        provider = "OpenAI"
        api_key = self.api_key_input.text()
        user_text = self.user_request.toPlainText()
        server_url = self.server_url_input.text().strip()
        # Use automatically determined database name
        database_name = self.database_name

        if not api_key or not user_text:
            self.sql_output.setPlainText("Error: Missing API key or request text.")
            return
        
        if not server_url:
            self.sql_output.setPlainText("Error: Missing MCP server URL.")
            return
        
        # Check server status before making request
        try:
            test_response = requests.get(f"{server_url.rstrip('/')}/docs", timeout=2)
            if test_response.status_code != 200:
                self._show_server_error_dialog(server_url)
                return
        except requests.exceptions.ConnectionError:
            self._show_server_error_dialog(server_url)
            return
        except Exception:
            # Continue anyway, let the actual request handle the error
            pass

        # Disable button during request
        self.refactor_btn.setEnabled(False)
        self.refactor_btn.setText("Processing...")
        self.sql_output.setPlainText("Sending request to MCP server...")
        self.schema_output.setPlainText("Fetching schema context...")
        self.validation_label.setText("Validating...")
        self.validation_label.setStyleSheet("color: orange;")

        # Build MCP server endpoint URL (new endpoint)
        mcp_url = f"{server_url.rstrip('/')}/nl_to_sql"

        payload = {
            "provider": provider,
            "api_key": api_key,
            "database": database_name,
            "user_request": user_text
        }

        # Create and start async request thread
        self.mcp_thread = MCPRequestThread(mcp_url, payload)
        self.mcp_thread.finished.connect(self.on_mcp_success)
        self.mcp_thread.error.connect(self.on_mcp_error)
        self.mcp_thread.start()
    
    def on_mcp_success(self, data: Dict[str, Any]):
        """Handle successful MCP server response."""
        self.refactor_btn.setEnabled(True)
        self.refactor_btn.setText("Refactor to SQLite Query")
        
        sql_query = data.get("sql_query", "")
        schema_context = data.get("schema_context", "")
        validation = data.get("validation", {})
        
        if sql_query:
            self.sql_output.setPlainText(sql_query)
            
            # Display schema context
            if schema_context:
                self.schema_output.setPlainText(schema_context)
            else:
                self.schema_output.setPlainText("No schema context available.")
            
            # Display validation status
            if validation:
                if validation.get("success"):
                    row_count = validation.get("preview_row_count", 0)
                    columns = validation.get("columns", [])
                    self.validation_label.setText(
                        f"✓ Valid ({row_count} rows, {len(columns)} columns)"
                    )
                    self.validation_label.setStyleSheet("color: green;")
                else:
                    error = validation.get("error", "Unknown error")
                    self.validation_label.setText(f"✗ Invalid: {error}")
                    self.validation_label.setStyleSheet("color: red;")
            else:
                self.validation_label.setText("Not validated")
                self.validation_label.setStyleSheet("color: gray;")
            
            # Clear results table (user can run query manually if needed)
            self.results_table.clear()
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
        else:
            self.sql_output.setPlainText("Error: No SQL query returned from server.")
            self.validation_label.setText("Error: No query generated")
            self.validation_label.setStyleSheet("color: red;")
    
    def _show_server_error_dialog(self, server_url: str):
        """Show formatted error dialog when server is not running."""
        error_text = (
            "⚠️ Server Not Running\n\n"
            f"The FastAPI server at {server_url} is not running.\n\n"
            "To start the server:\n\n"
            "1. Open a terminal\n"
            "2. Navigate to the demo directory:\n"
            "   cd demo\n\n"
            "3. Run one of these commands:\n"
            "   python start_server.py\n"
            "   OR\n"
            "   ./start_server.sh\n"
            "   OR\n"
            "   uvicorn api_call:app --host 0.0.0.0 --port 8000 --reload\n\n"
            "4. Wait for 'Application startup complete'\n"
            "5. Then try again in this GUI"
        )
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Server Not Running")
        msg_box.setText(error_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        
        # Update server status
        self.check_server_status()
    
    def on_mcp_error(self, error_msg: str):
        """Handle MCP server error."""
        self.refactor_btn.setEnabled(True)
        self.refactor_btn.setText("Refactor to SQLite Query")
        self.sql_output.setPlainText(f"Error: {error_msg}")
        self.validation_label.setText("Error occurred")
        self.validation_label.setStyleSheet("color: red;")
        
        # Check if it's a connection error and show formatted dialog
        if "Server not running" in error_msg or "Connection refused" in error_msg:
            server_url = self.server_url_input.text().strip()
            self._show_server_error_dialog(server_url)
        else:
            # Show standard error dialog for other errors
            QMessageBox.warning(self, "MCP Server Error", error_msg)
        
        # Update server status
        self.check_server_status()

    # ---------------------------------------------------------
    # STEP 2: Execute SQL query against SQLite DB
    # ---------------------------------------------------------
    def run_sql_query(self):
        sql_query = self.sql_output.toPlainText().strip()
        if not sql_query:
            QMessageBox.warning(self, "No Query", "No SQL query to run.")
            return

        # Use automatically determined database path
        db_path_obj = self.database_path
        
        if not db_path_obj.exists():
            QMessageBox.warning(
                self, 
                "Database Not Found", 
                f"Database file not found:\n{db_path_obj}\n\nPlease check the path."
            )
            return

        try:
            conn = sqlite3.connect(str(db_path_obj))
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            # Handle queries that don't return results (INSERT, UPDATE, DELETE)
            if cursor.description:
                headers = [desc[0] for desc in cursor.description]
                self.populate_table(headers, rows)
            else:
                # For non-SELECT queries, show success message
                conn.commit()
                self.results_table.clear()
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                QMessageBox.information(
                    self, 
                    "Query Executed", 
                    f"Query executed successfully.\nRows affected: {cursor.rowcount}"
                )

            conn.close()

        except sqlite3.Error as e:
            error_msg = f"SQLite error: {str(e)}"
            self.sql_output.setPlainText(f"{self.sql_output.toPlainText()}\n\n{error_msg}")
            QMessageBox.critical(self, "SQLite Error", error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.sql_output.setPlainText(f"{self.sql_output.toPlainText()}\n\n{error_msg}")
            QMessageBox.critical(self, "Error", error_msg)

    # ---------------------------------------------------------
    # STEP 3: Display results in table
    # ---------------------------------------------------------
    def populate_table(self, headers, rows):
        """Populate table with query results."""
        self.results_table.clear()
        self.results_table.setColumnCount(len(headers))
        self.results_table.setRowCount(len(rows))
        self.results_table.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.results_table.setItem(r, c, item)

        self.results_table.resizeColumnsToContents()
    
    def closeEvent(self, event):
        """Clean up server processes when window is closed."""
        servers_running = []
        
        if self.server_process and self.server_process.state() == QProcess.ProcessState.Running:
            servers_running.append("FastAPI server")
        
        if self.mcp_server_process and self.mcp_server_process.state() == QProcess.ProcessState.Running:
            servers_running.append("MCP server")
        
        if servers_running:
            server_list = " and ".join(servers_running)
            reply = QMessageBox.question(
                self,
                "Stop Servers?",
                f"The {server_list} {'are' if len(servers_running) > 1 else 'is'} still running. Do you want to stop {'them' if len(servers_running) > 1 else 'it'}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                if self.server_process and self.server_process.state() == QProcess.ProcessState.Running:
                    self.server_process.terminate()
                    if not self.server_process.waitForFinished(3000):
                        self.server_process.kill()
                
                if self.mcp_server_process and self.mcp_server_process.state() == QProcess.ProcessState.Running:
                    self.mcp_server_process.terminate()
                    if not self.mcp_server_process.waitForFinished(3000):
                        self.mcp_server_process.kill()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    window = LLMtoSQLiteApp()
    window.show()
    app.exec()