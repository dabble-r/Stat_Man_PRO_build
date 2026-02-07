"""
NL-to-SQL Server Management Utility

This module provides utilities for managing the FastAPI and MCP servers
used for natural language to SQL conversion.

Based on the server implementation guide in nl_sql/server_guide.md.

The manager:
1. Starts both servers as subprocesses using QProcess
2. Monitors server output and errors
3. Verifies servers are ready by checking health endpoints
4. Provides signals for server status updates
5. Handles server shutdown gracefully
"""

import sys
from pathlib import Path
from typing import Optional, Callable
from PySide6.QtCore import QProcess, QTimer, Signal, QObject


class NLServerManager(QObject):
    """
    Manages FastAPI and MCP servers for NL-to-SQL functionality.
    
    This class handles starting, stopping, and monitoring both servers
    using QProcess. It provides signals for status updates and errors.
    
    FastAPI Server (Port 8000):
    - Converts natural language to SQL queries using OpenAI
    - Communicates with MCP server to get database schema
    - Validates generated SQL queries
    
    MCP Server (Port 8001):
    - Implements JSON-RPC 2.0 protocol for SQLite database exploration
    - Provides database schema information
    - Executes read-only SQL queries
    """
    
    # Signals for server status updates
    fastapi_started = Signal()  # FastAPI server process started
    fastapi_failed = Signal(str)  # FastAPI server failed (error message)
    fastapi_ready = Signal()  # FastAPI server is responding
    
    mcp_started = Signal()  # MCP server process started
    mcp_failed = Signal(str)  # MCP server failed (error message)
    mcp_ready = Signal()  # MCP server is responding
    
    all_servers_ready = Signal()  # Both servers are ready and responding
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nl_sql_dir = self._get_nl_sql_directory()
        
        # FastAPI server process (Port 8000)
        self.fastapi_process: Optional[QProcess] = None
        self.fastapi_starting = False
        
        # MCP server process (Port 8001)
        self.mcp_process: Optional[QProcess] = None
        self.mcp_starting = False
        
        # Track server readiness
        self._fastapi_ready_flag = False
        self._mcp_ready_flag = False
        self._all_servers_ready_emitted = False  # Prevent multiple emissions
        
        # Callbacks for output/error handling
        self.fastapi_output_callback: Optional[Callable[[str], None]] = None
        self.fastapi_error_callback: Optional[Callable[[str], None]] = None
        self.mcp_output_callback: Optional[Callable[[str], None]] = None
        self.mcp_error_callback: Optional[Callable[[str], None]] = None
    
    def _get_nl_sql_directory(self) -> Path:
        """
        Get the absolute path to the nl_sql directory.
        
        The nl_sql directory contains:
        - api_call.py (FastAPI server)
        - mcp_server.py (MCP server)
        - start_server.py (FastAPI startup script)
        - start_mcp_server.py (MCP startup script)
        """
        # Get project root (assuming this file is in src/utils/)
        # Path structure: project_root/src/utils/nl_sql_server.py
        project_root = Path(__file__).parent.parent.parent
        nl_sql_dir = project_root / "nl_sql"
        
        if not nl_sql_dir.exists():
            raise FileNotFoundError(
                f"NL-SQL directory not found: {nl_sql_dir}\n"
                "Please ensure the nl_sql directory exists in the project root."
            )
        
        return nl_sql_dir.resolve()
    
    def start_fastapi_server(self, output_callback=None, error_callback=None):
        """
        Start the FastAPI server for NL-to-SQL (Port 8000).
        
        The FastAPI server:
        - Converts natural language to SQL queries using OpenAI
        - Communicates with MCP server to get database schema
        - Validates generated SQL queries
        - Endpoint: POST /nl_to_sql
        - API docs: http://localhost:8000/docs
        
        Args:
            output_callback: Optional callback for stdout output (str) -> None
            error_callback: Optional callback for stderr output (str) -> None
        """
        if self.fastapi_process and self.fastapi_process.state() == QProcess.ProcessState.Running:
            return  # Already running
        
        if self.fastapi_starting:
            return  # Already starting
        
        self.fastapi_starting = True
        self.fastapi_output_callback = output_callback
        self.fastapi_error_callback = error_callback
        
        # Create QProcess for FastAPI server
        self.fastapi_process = QProcess(self)
        self.fastapi_process.setWorkingDirectory(str(self.nl_sql_dir))
        
        # Connect signals to monitor server startup
        self.fastapi_process.readyReadStandardOutput.connect(self._on_fastapi_output)
        self.fastapi_process.readyReadStandardError.connect(self._on_fastapi_error)
        self.fastapi_process.finished.connect(self._on_fastapi_finished)
        self.fastapi_process.started.connect(self._on_fastapi_started)
        
        # Set environment - add both nl_sql directory and project root to PYTHONPATH
        # This ensures api_call.py and src modules can be imported
        env = self.fastapi_process.processEnvironment()
        project_root = self.nl_sql_dir.parent
        
        # Get current PYTHONPATH
        current_pythonpath = env.value("PYTHONPATH", "")
        pythonpath_parts = []
        
        # Add nl_sql directory first (for api_call.py)
        pythonpath_parts.append(str(self.nl_sql_dir))
        # Add project root (for src.utils imports)
        pythonpath_parts.append(str(project_root))
        
        # Preserve existing PYTHONPATH if present
        if current_pythonpath:
            pythonpath_parts.append(current_pythonpath)
        
        # Set new PYTHONPATH
        new_pythonpath = ":".join(pythonpath_parts)
        env.insert("PYTHONPATH", new_pythonpath)
        
        # Disable reload by default (causes issues with QProcess)
        env.insert("STATMANG_ENABLE_RELOAD", "false")
        
        self.fastapi_process.setProcessEnvironment(env)
        
        # Start the server using start_server.py script
        python_exe = sys.executable
        server_script = self.nl_sql_dir / "start_server.py"
        project_root = self.nl_sql_dir.parent
        new_pythonpath = env.value("PYTHONPATH", "")
        
        print(f"[NL Server Manager] FastAPI Server Startup:")
        print(f"  Working directory: {self.nl_sql_dir}")
        print(f"  Python executable: {python_exe}")
        print(f"  Script path: {server_script}")
        print(f"  Script exists: {server_script.exists()}")
        print(f"  Project root: {project_root}")
        print(f"  PYTHONPATH: {new_pythonpath}")
        
        if server_script.exists():
            # Use the startup script (recommended)
            # start_server.py handles:
            # - Adding nl_sql directory to Python path
            # - Verifying uvicorn and api_call can be imported
            # - Supporting reload mode (disabled by default for subprocess)
            print(f"[NL Server Manager] Starting FastAPI server: {server_script}")
            # Use absolute path to script
            script_path = str(server_script.resolve())
            success = self.fastapi_process.start(python_exe, [script_path])
        else:
            # Fallback: use uvicorn directly
            print(f"[NL Server Manager] Script not found, using uvicorn directly")
            success = self.fastapi_process.start(
                python_exe,
                ["-m", "uvicorn", "api_call:app", "--host", "0.0.0.0", "--port", "8000"]
            )
        
        if not success:
            self.fastapi_starting = False
            error_msg = self.fastapi_process.errorString()
            print(f"[NL Server Manager] Failed to start FastAPI server process: {error_msg}")
            self.fastapi_failed.emit(f"Failed to start process: {error_msg}")
            return
        
        print(f"[NL Server Manager] FastAPI server process started successfully")
        # Wait for server to start, then verify it's responding
        QTimer.singleShot(3000, self._verify_fastapi_ready)
    
    def start_mcp_server(self, output_callback=None, error_callback=None):
        """
        Start the MCP server for SQLite exploration (Port 8001).
        
        The MCP server:
        - Implements JSON-RPC 2.0 protocol for SQLite database exploration
        - Provides database schema information
        - Executes read-only SQL queries
        - Endpoint: POST /mcp
        - Health check: http://localhost:8001/health
        
        Args:
            output_callback: Optional callback for stdout output (str) -> None
            error_callback: Optional callback for stderr output (str) -> None
        """
        if self.mcp_process and self.mcp_process.state() == QProcess.ProcessState.Running:
            return  # Already running
        
        if self.mcp_starting:
            return  # Already starting
        
        self.mcp_starting = True
        self.mcp_output_callback = output_callback
        self.mcp_error_callback = error_callback
        
        # Create QProcess for MCP server
        self.mcp_process = QProcess(self)
        self.mcp_process.setWorkingDirectory(str(self.nl_sql_dir))
        
        # Connect signals to monitor server startup
        self.mcp_process.readyReadStandardOutput.connect(self._on_mcp_output)
        self.mcp_process.readyReadStandardError.connect(self._on_mcp_error)
        self.mcp_process.finished.connect(self._on_mcp_finished)
        self.mcp_process.started.connect(self._on_mcp_started)
        
        # Set environment - add both nl_sql directory and project root to PYTHONPATH
        # This ensures mcp_server.py and src modules can be imported
        env = self.mcp_process.processEnvironment()
        project_root = self.nl_sql_dir.parent
        
        # Get current PYTHONPATH
        current_pythonpath = env.value("PYTHONPATH", "")
        pythonpath_parts = []
        
        # Add nl_sql directory first (for mcp_server.py)
        pythonpath_parts.append(str(self.nl_sql_dir))
        # Add project root (for src.utils imports)
        pythonpath_parts.append(str(project_root))
        
        # Preserve existing PYTHONPATH if present
        if current_pythonpath:
            pythonpath_parts.append(current_pythonpath)
        
        # Set new PYTHONPATH
        new_pythonpath = ":".join(pythonpath_parts)
        env.insert("PYTHONPATH", new_pythonpath)
        
        # Disable reload by default (causes issues with QProcess)
        env.insert("STATMANG_ENABLE_RELOAD", "false")
        
        self.mcp_process.setProcessEnvironment(env)
        
        # Start the server using start_mcp_server.py script
        python_exe = sys.executable
        mcp_script = self.nl_sql_dir / "start_mcp_server.py"
        
        project_root = self.nl_sql_dir.parent
        new_pythonpath = env.value("PYTHONPATH", "")
        
        print(f"[NL Server Manager] MCP Server Startup:")
        print(f"  Working directory: {self.nl_sql_dir}")
        print(f"  Python executable: {python_exe}")
        print(f"  Script path: {mcp_script}")
        print(f"  Script exists: {mcp_script.exists()}")
        print(f"  Project root: {project_root}")
        print(f"  PYTHONPATH: {new_pythonpath}")
        
        if mcp_script.exists():
            # Use the startup script (recommended)
            # start_mcp_server.py handles:
            # - Adding nl_sql directory to Python path
            # - Verifying uvicorn and mcp_server can be imported
            # - Supporting reload mode (disabled by default for subprocess)
            print(f"[NL Server Manager] Starting MCP server: {mcp_script}")
            # Use absolute path to script
            script_path = str(mcp_script.resolve())
            success = self.mcp_process.start(python_exe, [script_path])
        else:
            # Fallback: use uvicorn directly with proper module path
            print(f"[NL Server Manager] Script not found, using uvicorn directly")
            # Change to nl_sql directory and run uvicorn
            success = self.mcp_process.start(
                python_exe,
                ["-m", "uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8001", "--no-reload"]
            )
        
        if not success:
            self.mcp_starting = False
            error_msg = self.mcp_process.errorString()
            print(f"[NL Server Manager] Failed to start MCP server process: {error_msg}")
            self.mcp_failed.emit(f"Failed to start process: {error_msg}")
            return
        
        print(f"[NL Server Manager] MCP server process started successfully")
        # Wait for server to start, then verify it's responding
        QTimer.singleShot(3000, self._verify_mcp_ready)
    
    def stop_fastapi_server(self):
        """Stop the FastAPI server gracefully."""
        if self.fastapi_process:
            self.fastapi_process.terminate()
            if not self.fastapi_process.waitForFinished(3000):
                self.fastapi_process.kill()
            self.fastapi_process = None
        self.fastapi_starting = False
        self._fastapi_ready_flag = False
        self._all_servers_ready_emitted = False  # Reset when server stops
    
    def stop_mcp_server(self):
        """Stop the MCP server gracefully."""
        if self.mcp_process:
            self.mcp_process.terminate()
            if not self.mcp_process.waitForFinished(3000):
                self.mcp_process.kill()
            self.mcp_process = None
        self.mcp_starting = False
        self._mcp_ready_flag = False
        self._all_servers_ready_emitted = False  # Reset when server stops
    
    def stop_all_servers(self):
        """Stop both servers gracefully."""
        self.stop_fastapi_server()
        self.stop_mcp_server()
    
    def is_fastapi_running(self) -> bool:
        """Check if FastAPI server process is running."""
        return (self.fastapi_process is not None and 
                self.fastapi_process.state() == QProcess.ProcessState.Running)
    
    def is_mcp_running(self) -> bool:
        """Check if MCP server process is running."""
        return (self.mcp_process is not None and 
                self.mcp_process.state() == QProcess.ProcessState.Running)
    
    def start_all_servers(self, output_callback=None, error_callback=None):
        """
        Start both FastAPI and MCP servers.
        
        This is a convenience method that starts both servers simultaneously.
        The all_servers_ready signal will be emitted when both servers are ready.
        
        Args:
            output_callback: Optional callback for stdout output from both servers (str) -> None
            error_callback: Optional callback for stderr output from both servers (str) -> None
        """
        # Start both servers
        self.start_fastapi_server(output_callback=output_callback, error_callback=error_callback)
        self.start_mcp_server(output_callback=output_callback, error_callback=error_callback)
    
    def are_all_servers_ready(self) -> bool:
        """
        Check if both servers are ready and responding.
        
        Returns:
            True if both FastAPI and MCP servers are ready, False otherwise
        """
        return self._fastapi_ready_flag and self._mcp_ready_flag
    
    def _check_all_servers_ready(self):
        """Check if both servers are ready and emit all_servers_ready signal if so."""
        if self._fastapi_ready_flag and self._mcp_ready_flag:
            if not self._all_servers_ready_emitted:
                print("[NL Server Manager] All servers are ready")
                self._all_servers_ready_emitted = True
                self.all_servers_ready.emit()
    
    # FastAPI server signal handlers
    
    def _on_fastapi_started(self):
        """Called when FastAPI server process starts."""
        print("[NL Server Manager] FastAPI server process started")
        self.fastapi_started.emit()
    
    def _on_fastapi_output(self):
        """Handle FastAPI server stdout output."""
        if not self.fastapi_process:
            return
        
        output = bytes(self.fastapi_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if output.strip():
            print(f"[NL FastAPI Server Output] {output.strip()}")
            if self.fastapi_output_callback:
                self.fastapi_output_callback(output)
            
            # Look for startup confirmation messages
            # These indicate the server is starting up
            if any(phrase in output for phrase in [
                "Application startup complete",
                "Uvicorn running",
                "Started server process",
                "Waiting for application startup"
            ]):
                # Server is starting up, verify it's ready
                QTimer.singleShot(2000, self._verify_fastapi_ready)
    
    def _on_fastapi_error(self):
        """Handle FastAPI server stderr output."""
        if not self.fastapi_process:
            return
        
        error = bytes(self.fastapi_process.readAllStandardError()).decode('utf-8', errors='ignore')
        if error.strip():
            print(f"[NL FastAPI Server Error] {error.strip()}")
            if self.fastapi_error_callback:
                self.fastapi_error_callback(error)
            
            # Check for specific errors that should stop startup immediately
            error_lower = error.lower()
            if "uvicorn is not installed" in error_lower or "no module named 'uvicorn'" in error_lower:
                self.fastapi_starting = False
                self.fastapi_failed.emit(
                    "uvicorn is not installed. Install with: pip install fastapi uvicorn openai"
                )
            elif "module not found" in error_lower or "no module named" in error_lower:
                # Missing dependencies - let _on_fastapi_finished handle with full output
                self.fastapi_starting = False
            elif "address already in use" in error_lower or "port 8000" in error_lower:
                # Port might be in use - check if server is actually running
                QTimer.singleShot(1000, self._verify_fastapi_ready)
            # Note: Other errors might be warnings, so we don't stop startup immediately
    
    def _on_fastapi_finished(self, exit_code, exit_status):
        """Called when FastAPI server process finishes."""
        self.fastapi_starting = False
        # Reset ready flag if server crashed/stopped
        if exit_code != 0 or exit_status != QProcess.ExitStatus.NormalExit:
            self._fastapi_ready_flag = False
            self._all_servers_ready_emitted = False
        if exit_code != 0:
            # Read both stderr and stdout for complete error information
            error_output = ""
            stdout_output = ""
            
            if self.fastapi_process:
                error_bytes = self.fastapi_process.readAllStandardError()
                if error_bytes:
                    error_output = bytes(error_bytes).decode('utf-8', errors='ignore')
                
                stdout_bytes = self.fastapi_process.readAllStandardOutput()
                if stdout_bytes:
                    stdout_output = bytes(stdout_bytes).decode('utf-8', errors='ignore')
            
            print(f"[NL Server Manager] FastAPI server exited with code {exit_code}")
            
            # Combine outputs for better error detection
            combined_output = (error_output + "\n" + stdout_output).strip()
            
            if combined_output:
                print(f"[NL Server Manager] Error output:\n{combined_output}")
                
                # Check for common errors and provide helpful messages
                combined_lower = combined_output.lower()
                if "uvicorn is not installed" in combined_lower or "no module named 'uvicorn'" in combined_lower:
                    self.fastapi_failed.emit(
                        "ERROR: uvicorn is not installed.\n\n"
                        "Install required packages with:\n"
                        "  pip install fastapi uvicorn openai"
                    )
                elif "fastapi" in combined_lower and ("not installed" in combined_lower or "no module named" in combined_lower):
                    self.fastapi_failed.emit(
                        "ERROR: fastapi is not installed.\n\n"
                        "Install required packages with:\n"
                        "  pip install fastapi uvicorn openai"
                    )
                elif "openai" in combined_lower and ("not installed" in combined_lower or "no module named" in combined_lower):
                    self.fastapi_failed.emit(
                        "ERROR: openai is not installed.\n\n"
                        "Install required packages with:\n"
                        "  pip install fastapi uvicorn openai"
                    )
                elif "failed to import" in combined_lower or ("import" in combined_lower and "error" in combined_lower):
                    self.fastapi_failed.emit(
                        f"Import error:\n\n{combined_output[:500]}\n\n"
                        "Install required packages with:\n"
                        "  pip install fastapi uvicorn openai"
                    )
                else:
                    # Show the actual error output
                    self.fastapi_failed.emit(combined_output[:1000])  # Limit length
            else:
                self.fastapi_failed.emit(f"Server exited with code {exit_code} (no error output available)")
    
    def _verify_fastapi_ready(self):
        """
        Verify that FastAPI server is ready and responding.
        
        Checks the /docs endpoint to confirm server is running.
        """
        import requests
        try:
            response = requests.get("http://localhost:8000/docs", timeout=2)
            if response.status_code == 200:
                print("[NL Server Manager] FastAPI server is ready")
                self.fastapi_starting = False
                self._fastapi_ready_flag = True
                self.fastapi_ready.emit()
                # Check if both servers are ready
                self._check_all_servers_ready()
            else:
                # Server might still be starting
                if self.fastapi_starting:
                    QTimer.singleShot(2000, self._verify_fastapi_ready)
        except Exception:
            # Server might still be starting
            if self.fastapi_starting:
                QTimer.singleShot(2000, self._verify_fastapi_ready)
    
    # MCP server signal handlers
    
    def _on_mcp_started(self):
        """Called when MCP server process starts."""
        print("[NL Server Manager] MCP server process started")
        self.mcp_started.emit()
    
    def _on_mcp_output(self):
        """Handle MCP server stdout output."""
        if not self.mcp_process:
            return
        
        output = bytes(self.mcp_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if output.strip():
            print(f"[NL MCP Server Output] {output.strip()}")
            if self.mcp_output_callback:
                self.mcp_output_callback(output)
            
            # Look for startup confirmation messages
            # These indicate the server is starting up
            if any(phrase in output for phrase in [
                "Application startup complete",
                "Uvicorn running",
                "Started server process",
                "Waiting for application startup"
            ]):
                # Server is starting up, verify it's ready
                QTimer.singleShot(2000, self._verify_mcp_ready)
    
    def _on_mcp_error(self):
        """Handle MCP server stderr output."""
        if not self.mcp_process:
            return
        
        error = bytes(self.mcp_process.readAllStandardError()).decode('utf-8', errors='ignore')
        if error.strip():
            print(f"[NL MCP Server Error] {error.strip()}")
            if self.mcp_error_callback:
                self.mcp_error_callback(error)
            
            # Check for specific errors that should stop startup immediately
            error_lower = error.lower()
            if "uvicorn is not installed" in error_lower or "no module named 'uvicorn'" in error_lower:
                self.mcp_starting = False
                self.mcp_failed.emit(
                    "uvicorn is not installed. Install with: pip install fastapi uvicorn"
                )
            elif "module not found" in error_lower or "no module named" in error_lower:
                # Missing dependencies - let _on_mcp_finished handle with full output
                self.mcp_starting = False
            elif "address already in use" in error_lower or "port 8001" in error_lower:
                # Port might be in use - check if server is actually running
                QTimer.singleShot(1000, self._verify_mcp_ready)
            # Note: Other errors might be warnings, so we don't stop startup immediately
    
    def _on_mcp_finished(self, exit_code, exit_status):
        """Called when MCP server process finishes."""
        self.mcp_starting = False
        # Reset ready flag if server crashed/stopped
        if exit_code != 0 or exit_status != QProcess.ExitStatus.NormalExit:
            self._mcp_ready_flag = False
            self._all_servers_ready_emitted = False
        if exit_code != 0:
            # Read both stderr and stdout for complete error information
            error_output = ""
            stdout_output = ""
            
            if self.mcp_process:
                error_bytes = self.mcp_process.readAllStandardError()
                if error_bytes:
                    error_output = bytes(error_bytes).decode('utf-8', errors='ignore')
                
                stdout_bytes = self.mcp_process.readAllStandardOutput()
                if stdout_bytes:
                    stdout_output = bytes(stdout_bytes).decode('utf-8', errors='ignore')
            
            print(f"[NL Server Manager] MCP server exited with code {exit_code}")
            
            # Combine outputs for better error detection
            combined_output = (error_output + "\n" + stdout_output).strip()
            
            if combined_output:
                print(f"[NL Server Manager] Error output:\n{combined_output}")
                
                # Check for common errors and provide helpful messages
                combined_lower = combined_output.lower()
                if "uvicorn is not installed" in combined_lower or "no module named 'uvicorn'" in combined_lower:
                    self.mcp_failed.emit(
                        "ERROR: uvicorn is not installed.\n\n"
                        "Install required packages with:\n"
                        "  pip install fastapi uvicorn"
                    )
                elif "fastapi" in combined_lower and ("not installed" in combined_lower or "no module named" in combined_lower):
                    self.mcp_failed.emit(
                        "ERROR: fastapi is not installed.\n\n"
                        "Install required packages with:\n"
                        "  pip install fastapi uvicorn"
                    )
                elif "failed to import" in combined_lower or ("import" in combined_lower and "error" in combined_lower):
                    self.mcp_failed.emit(
                        f"Import error:\n\n{combined_output[:500]}\n\n"
                        "Install required packages with:\n"
                        "  pip install fastapi uvicorn"
                    )
                else:
                    # Show the actual error output
                    self.mcp_failed.emit(combined_output[:1000])  # Limit length
            else:
                self.mcp_failed.emit(f"Server exited with code {exit_code} (no error output available)")
    
    def _verify_mcp_ready(self):
        """
        Verify that MCP server is ready and responding.
        
        Checks the /health endpoint to confirm server is running.
        """
        import requests
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("[NL Server Manager] MCP server is ready")
                self.mcp_starting = False
                self._mcp_ready_flag = True
                self.mcp_ready.emit()
                # Check if both servers are ready
                self._check_all_servers_ready()
            else:
                # Server might still be starting
                if self.mcp_starting:
                    QTimer.singleShot(2000, self._verify_mcp_ready)
        except Exception:
            # Server might still be starting
            if self.mcp_starting:
                QTimer.singleShot(2000, self._verify_mcp_ready)
