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
import os
import shutil
import socket
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from PySide6.QtCore import QProcess, QTimer, Signal, QObject

from src.utils.path_resolver import get_app_base_path, get_database_path


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
        
        # Store accumulated output/error for better error reporting
        self._fastapi_stdout_buffer: list = []
        self._fastapi_stderr_buffer: list = []
        self._mcp_stdout_buffer: list = []
        self._mcp_stderr_buffer: list = []
        
        # Setup file logging
        self._setup_file_logging()
    
    def _get_nl_sql_directory(self) -> Path:
        """
        Get the absolute path to the nl_sql directory.

        The nl_sql directory contains:
        - api_call.py (FastAPI server)
        - mcp_server.py (MCP server)
        - start_server.py (FastAPI startup script)
        - start_mcp_server.py (MCP startup script)

        When running as a frozen exe, nl_sql is under the bundle root (sys._MEIPASS).
        """
        if getattr(sys, "frozen", False):
            project_root = Path(sys._MEIPASS)
        else:
            # Path structure: project_root/src/utils/nl_sql_server.py
            project_root = Path(__file__).parent.parent.parent
        nl_sql_dir = project_root / "nl_sql"

        if not nl_sql_dir.exists():
            raise FileNotFoundError(
                f"NL-SQL directory not found: {nl_sql_dir}\n"
                "Please ensure the nl_sql directory exists in the project root (or is bundled)."
            )

        return nl_sql_dir.resolve()

    def _get_python_executable(self) -> str:
        """
        Return the Python executable to use for server subprocesses.
        When frozen (onefile exe), sys.executable is the exe itself, so we must
        use a system Python; otherwise the subprocess would re-run the app.
        """
        if not getattr(sys, "frozen", False):
            return sys.executable
        # Prefer python3 then python so server scripts run with a real interpreter
        for name in ("python3", "python"):
            exe = shutil.which(name)
            if exe:
                return exe
        # Fallback: sys.executable will launch the exe again; log and return it
        print(
            "[NL Server Manager] Warning: No system Python found (python3/python). "
            "NL servers may not start from the built exe. Install Python and add to PATH."
        )
        return sys.executable

    def _setup_file_logging(self):
        """Setup file logging for server output."""
        # When frozen, use app base (next to exe) for writable logs; else project tests/logs
        if getattr(sys, "frozen", False):
            project_root = Path(get_app_base_path())
            logs_dir = project_root / "logs"
        else:
            project_root = Path(__file__).parent.parent.parent
            logs_dir = project_root / "tests" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup FastAPI server log file
        fastapi_log_file = logs_dir / "fastapi_server.log"
        self._fastapi_logger = logging.getLogger("fastapi_server")
        self._fastapi_logger.setLevel(logging.DEBUG)
        # Remove existing handlers to avoid duplicates
        self._fastapi_logger.handlers.clear()
        fastapi_handler = logging.FileHandler(fastapi_log_file, mode='a', encoding='utf-8')
        fastapi_handler.setLevel(logging.DEBUG)
        fastapi_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fastapi_handler.setFormatter(fastapi_formatter)
        self._fastapi_logger.addHandler(fastapi_handler)
        self._fastapi_logger.propagate = False
        
        # Setup MCP server log file
        mcp_log_file = logs_dir / "mcp_server.log"
        self._mcp_logger = logging.getLogger("mcp_server")
        self._mcp_logger.setLevel(logging.DEBUG)
        # Remove existing handlers to avoid duplicates
        self._mcp_logger.handlers.clear()
        mcp_handler = logging.FileHandler(mcp_log_file, mode='a', encoding='utf-8')
        mcp_handler.setLevel(logging.DEBUG)
        mcp_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        mcp_handler.setFormatter(mcp_formatter)
        self._mcp_logger.addHandler(mcp_handler)
        self._mcp_logger.propagate = False
        
        # Log initialization
        self._fastapi_logger.info("=" * 80)
        self._fastapi_logger.info(f"FastAPI Server Logging Initialized - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._fastapi_logger.info(f"NLServerManager instance created - PID: {os.getpid()}")
        self._mcp_logger.info("=" * 80)
        self._mcp_logger.info(f"MCP Server Logging Initialized - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._mcp_logger.info(f"NLServerManager instance created - PID: {os.getpid()}")
    
    def _check_and_free_port(self, port: int) -> bool:
        """
        Check if a port is in use and free it if necessary.
        
        Returns True if port is free (or was successfully freed), False otherwise.
        """
        try:
            # First, try to use lsof to check if anything is using the port
            # This is more reliable than trying to connect/bind
            if sys.platform != 'win32':
                try:
                    result = subprocess.run(
                        ['lsof', '-ti', f':{port}'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        # Port is in use - kill the process(es)
                        pids = result.stdout.strip().split('\n')
                        print(f"[NL Server Manager] Port {port} is in use by process(es): {', '.join(pids)}")
                        for pid in pids:
                            if pid.strip():
                                print(f"[NL Server Manager] Killing process {pid} using port {port}")
                                subprocess.run(
                                    ['kill', '-9', pid.strip()],
                                    check=False,
                                    timeout=5
                                )
                        # Wait for cleanup
                        time.sleep(1.5)
                        # Verify port is now free
                        result2 = subprocess.run(
                            ['lsof', '-ti', f':{port}'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if result2.returncode == 0 and result2.stdout.strip():
                            print(f"[NL Server Manager] Warning: Port {port} still in use after kill attempt")
                            return False
                        else:
                            print(f"[NL Server Manager] Port {port} successfully freed")
                            return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # lsof not available or timeout - fall back to socket check
                    pass
            
            # Fallback: Check if port is in use by trying to connect to it
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                # Port is in use (connection succeeded), but lsof didn't find it
                # This might be a TIME_WAIT state or the process died
                # Try lsof one more time with a longer wait
                print(f"[NL Server Manager] Port {port} appears in use (connection check), attempting to free...")
                if sys.platform != 'win32':
                    try:
                        time.sleep(0.5)  # Brief wait for TIME_WAIT to clear
                        result = subprocess.run(
                            ['lsof', '-ti', f':{port}'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            pids = result.stdout.strip().split('\n')
                            for pid in pids:
                                if pid.strip():
                                    print(f"[NL Server Manager] Killing process {pid} using port {port}")
                                    subprocess.run(
                                        ['kill', '-9', pid.strip()],
                                        check=False,
                                        timeout=5
                                    )
                            time.sleep(1.5)
                            # Verify
                            result2 = subprocess.run(
                                ['lsof', '-ti', f':{port}'],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if result2.returncode == 0 and result2.stdout.strip():
                                return False
                            else:
                                print(f"[NL Server Manager] Port {port} freed after connection check")
                                return True
                    except Exception:
                        pass
                # If we can't free it, return False
                print(f"[NL Server Manager] Could not free port {port} (may be in TIME_WAIT state)")
                return False
            else:
                # Port is free
                return True
        except Exception as e:
            print(f"[NL Server Manager] Error checking port {port}: {e}")
            # If we can't check, assume it's okay and let the server try
            return True
    
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
        # Log server start attempt
        if hasattr(self, '_fastapi_logger'):
            self._fastapi_logger.info("\n\n" + "=" * 80)
            self._fastapi_logger.info(f"Attempting to start FastAPI server - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._fastapi_logger.info(f"Current process state: {self.fastapi_process.state() if self.fastapi_process else 'No process'}")
            self._fastapi_logger.info(f"Already starting: {self.fastapi_starting}")
        
        if self.fastapi_process and self.fastapi_process.state() == QProcess.ProcessState.Running:
            if hasattr(self, '_fastapi_logger'):
                self._fastapi_logger.info("FastAPI server already running, skipping start")
            return  # Already running
        
        if self.fastapi_starting:
            if hasattr(self, '_fastapi_logger'):
                self._fastapi_logger.info("FastAPI server already starting, skipping start")
            return  # Already starting
        
        # Check and free port 8000 before starting
        port_freed = self._check_and_free_port(8000)
        if hasattr(self, '_fastapi_logger'):
            self._fastapi_logger.info(f"Port 8000 check result: {'Freed' if port_freed else 'Already free or could not free'}")
        # Small delay to ensure port is fully released
        time.sleep(0.3)
        
        self.fastapi_starting = True
        self.fastapi_output_callback = output_callback
        self.fastapi_error_callback = error_callback
        
        # Clear output buffers for new server start
        self._fastapi_stdout_buffer = []
        self._fastapi_stderr_buffer = []
        
        if hasattr(self, '_fastapi_logger'):
            self._fastapi_logger.info("FastAPI server startup initiated")
        
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
        new_pythonpath = os.pathsep.join(pythonpath_parts)
        env.insert("PYTHONPATH", new_pythonpath)
        
        # Disable reload by default (causes issues with QProcess)
        env.insert("STATMANG_ENABLE_RELOAD", "false")
        
        # When frozen, server subprocess (system Python) must use same app base and DB as main app
        if getattr(sys, "frozen", False):
            env.insert("STATMANG_APP_BASE", get_app_base_path())
            env.insert("STATMANG_DB_PATH", str(get_database_path()))
        
        # IMPORTANT: Pass OPENAI_API_KEY from parent process environment to subprocess
        # This allows the API key set in the dialog to be available in the server subprocess
        parent_openai_key = os.getenv("OPENAI_API_KEY")
        if parent_openai_key:
            env.insert("OPENAI_API_KEY", parent_openai_key)
            print(f"[NL Server Manager] Passing OPENAI_API_KEY to FastAPI server subprocess")
        
        # Pass network-related environment variables for proxy/SSL support
        network_vars = [
            "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
            "NO_PROXY", "no_proxy",
            "SSL_CERT_FILE", "SSL_CERT_DIR",
            "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"
        ]
        for var in network_vars:
            if var in os.environ:
                env.insert(var, os.environ[var])
                print(f"[NL Server Manager] Passing {var} to FastAPI server subprocess")
        
        self.fastapi_process.setProcessEnvironment(env)
        
        # Start the server using start_server.py script
        python_exe = self._get_python_executable()
        server_script = self.nl_sql_dir / "start_server.py"
        project_root = self.nl_sql_dir.parent
        new_pythonpath = env.value("PYTHONPATH", "")
        
        print("\n\n[NL Server Manager] FastAPI Server Startup:")
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
            # Final port check right before starting
            if not self._check_and_free_port(8000):
                print("[NL Server Manager] Warning: Port 8000 may still be in use, attempting server start anyway")
            time.sleep(0.2)  # Brief delay to ensure port is free
            success = self.fastapi_process.start(python_exe, [script_path])
        else:
            # Fallback: use uvicorn directly
            if hasattr(self, '_fastapi_logger'):
                self._fastapi_logger.warning("Script not found, using uvicorn directly")
            print(f"[NL Server Manager] Script not found, using uvicorn directly")
            success = self.fastapi_process.start(
                python_exe,
                ["-m", "uvicorn", "api_call:app", "--host", "0.0.0.0", "--port", "8000"]
            )
        
        # Log QProcess.start() result
        if hasattr(self, '_fastapi_logger'):
            self._fastapi_logger.info(f"QProcess.start() returned: {success}")
            self._fastapi_logger.info(f"Process state after start: {self.fastapi_process.state()}")
            if success:
                self._fastapi_logger.info("Waiting for 'started' signal from QProcess...")
        
        # Don't immediately fail - QProcess.start() can return False even if process will start
        # Instead, wait a moment and check process state, or rely on started/finished signals
        if not success:
            # Give process a moment to actually start (QProcess.start() is asynchronous)
            # Check after 1 second if process actually failed or if it started successfully
            QTimer.singleShot(1000, lambda: self._check_process_start_result('fastapi'))
            # Don't return - let the timeout handler check if it actually failed
            # The started signal will be emitted if it succeeds
        else:
            print(f"[NL Server Manager] FastAPI server process start() returned success")
        
        # Wait for server to start, then verify it's responding
        # This will be called regardless of initial start() return value
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
        
        # Check and free port 8001 before starting
        if not self._check_and_free_port(8001):
            print("[NL Server Manager] Warning: Port 8001 might be in use, but proceeding with server start")
            # Don't fail here - let the server try and handle the error if it occurs
        
        self.mcp_starting = True
        self.mcp_output_callback = output_callback
        self.mcp_error_callback = error_callback
        
        # Clear output buffers for new server start
        self._mcp_stdout_buffer = []
        self._mcp_stderr_buffer = []
        
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
        new_pythonpath = os.pathsep.join(pythonpath_parts)
        env.insert("PYTHONPATH", new_pythonpath)
        
        # Disable reload by default (causes issues with QProcess)
        env.insert("STATMANG_ENABLE_RELOAD", "false")
        
        # When frozen, server subprocess (system Python) must use same app base and DB as main app
        if getattr(sys, "frozen", False):
            env.insert("STATMANG_APP_BASE", get_app_base_path())
            env.insert("STATMANG_DB_PATH", str(get_database_path()))
        
        self.mcp_process.setProcessEnvironment(env)
        
        # Start the server using start_mcp_server.py script
        python_exe = self._get_python_executable()
        mcp_script = self.nl_sql_dir / "start_mcp_server.py"
        
        project_root = self.nl_sql_dir.parent
        new_pythonpath = env.value("PYTHONPATH", "")
        
        print("\n\n[NL Server Manager] MCP Server Startup:")
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
            # Final port check right before starting
            if not self._check_and_free_port(8001):
                print("[NL Server Manager] Warning: Port 8001 may still be in use, attempting server start anyway")
            time.sleep(0.2)  # Brief delay to ensure port is free
            success = self.mcp_process.start(python_exe, [script_path])
        else:
            # Fallback: use uvicorn directly with proper module path
            print(f"[NL Server Manager] Script not found, using uvicorn directly")
            # Change to nl_sql directory and run uvicorn
            success = self.mcp_process.start(
                python_exe,
                ["-m", "uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8001", "--no-reload"]
            )
        
        # Don't immediately fail - QProcess.start() can return False even if process will start
        # Instead, wait a moment and check process state, or rely on started/finished signals
        if not success:
            # Give process a moment to actually start (QProcess.start() is asynchronous)
            # Check after 1 second if process actually failed or if it started successfully
            QTimer.singleShot(1000, lambda: self._check_process_start_result('mcp'))
            # Don't return - let the timeout handler check if it actually failed
            # The started signal will be emitted if it succeeds
        else:
            print(f"[NL Server Manager] MCP server process start() returned success")
        
        # Wait for server to start, then verify it's responding
        # This will be called regardless of initial start() return value
        QTimer.singleShot(3000, self._verify_mcp_ready)
    
    def stop_fastapi_server(self):
        """Stop the FastAPI server gracefully."""
        if self.fastapi_process:
            self.fastapi_process.terminate()
            if not self.fastapi_process.waitForFinished(3000):
                self.fastapi_process.kill()
                self.fastapi_process.waitForFinished(2000)  # Wait longer after kill
            self.fastapi_process = None
        self.fastapi_starting = False
        self._fastapi_ready_flag = False
        self._all_servers_ready_emitted = False  # Reset when server stops
        # Ensure port is free after stopping
        self._check_and_free_port(8000)
    
    def stop_mcp_server(self):
        """Stop the MCP server gracefully."""
        if self.mcp_process:
            self.mcp_process.terminate()
            if not self.mcp_process.waitForFinished(3000):
                self.mcp_process.kill()
                self.mcp_process.waitForFinished(2000)  # Wait longer after kill
            self.mcp_process = None
        self.mcp_starting = False
        self._mcp_ready_flag = False
        self._all_servers_ready_emitted = False  # Reset when server stops
        # Ensure port is free after stopping
        self._check_and_free_port(8001)
    
    def stop_all_servers(self):
        """Stop both servers gracefully."""
        print("\n\n[NL Server Manager] Stopping all servers...")
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
                print("\n\n[NL Server Manager] All servers are ready")
                self._all_servers_ready_emitted = True
                self.all_servers_ready.emit()
    
    def _check_process_start_result(self, server_type: str):
        """
        Check if process actually started after initial start() call.
        
        This is called 1 second after QProcess.start() returns False to verify
        if the process actually failed or if it started successfully (since
        QProcess.start() is asynchronous and can return False even when the
        process will start successfully).
        
        Args:
            server_type: 'fastapi' or 'mcp'
        """
        if server_type == 'fastapi':
            process = self.fastapi_process
            starting_flag = self.fastapi_starting
            failed_signal = self.fastapi_failed
            script = self.nl_sql_dir / "start_server.py"
        else:  # mcp
            process = self.mcp_process
            starting_flag = self.mcp_starting
            failed_signal = self.mcp_failed
            script = self.nl_sql_dir / "start_mcp_server.py"
        
        if not process or not starting_flag:
            return
        
        state = process.state()
        if state == QProcess.ProcessState.NotRunning:
            # Process is not running - check if it actually failed or is still starting
            # Sometimes QProcess.start() returns False but process is still initializing
            # Wait a bit longer before declaring failure
            QTimer.singleShot(2000, lambda: self._check_process_start_result_delayed(server_type))
            print(f"[NL Server Manager] {server_type.upper()} server process not running yet, checking again in 2 seconds...")
        # If state is Starting or Running, the process is starting/started successfully
        # The started signal will be emitted, so we don't need to do anything here
        elif state in (QProcess.ProcessState.Starting, QProcess.ProcessState.Running):
            print(f"[NL Server Manager] {server_type.upper()} server process is {state.name} - waiting for started signal")
    
    def _check_process_start_result_delayed(self, server_type: str):
        """
        Delayed check for process start result (called 2 seconds after initial check).
        
        This gives the process more time to actually start before declaring failure.
        """
        if server_type == 'fastapi':
            process = self.fastapi_process
            starting_flag = self.fastapi_starting
            failed_signal = self.fastapi_failed
            script = self.nl_sql_dir / "start_server.py"
        else:  # mcp
            process = self.mcp_process
            starting_flag = self.mcp_starting
            failed_signal = self.mcp_failed
            script = self.nl_sql_dir / "start_mcp_server.py"
        
        if not process or not starting_flag:
            return
        
        state = process.state()
        if state == QProcess.ProcessState.NotRunning:
            # Process still not running after additional wait - this is a real failure
            error_msg = process.errorString()
            if not error_msg or error_msg == "Unknown error":
                # Try to get more specific error
                python_exe = self._get_python_executable()
                
                if not Path(python_exe).exists():
                    error_msg = f"Python executable not found: {python_exe}"
                elif not script.exists():
                    error_msg = f"Server script not found: {script}"
                else:
                    error_msg = "Process failed to start. Check logs for details."
            
            if server_type == 'fastapi':
                self.fastapi_starting = False
            else:
                self.mcp_starting = False
            
            print(f"\n\n[NL Server Manager] Failed to start {server_type.upper()} server process after delayed check: {error_msg}")
            failed_signal.emit(f"Failed to start process: {error_msg}")
        elif state in (QProcess.ProcessState.Starting, QProcess.ProcessState.Running):
            # Process is starting/running - success, don't emit failure
            print(f"\n\n[NL Server Manager] {server_type.upper()} server process is {state.name} - startup successful")
    
    # FastAPI server signal handlers
    
    def _on_fastapi_started(self):
        """Called when FastAPI server process starts."""
        if hasattr(self, '_fastapi_logger'):
            self._fastapi_logger.info("\n\n" + "=" * 80)
            self._fastapi_logger.info("FastAPI server process STARTED successfully")
            self._fastapi_logger.info(f"Process PID: {self.fastapi_process.processId() if self.fastapi_process else 'Unknown'}")
            self._fastapi_logger.info(f"Process state: {self.fastapi_process.state() if self.fastapi_process else 'Unknown'}")
        print("\n\n[NL Server Manager] FastAPI server process started")
        self.fastapi_started.emit()
    
    def _on_fastapi_output(self):
        """Handle FastAPI server stdout output."""
        if not self.fastapi_process:
            return
        
        output = bytes(self.fastapi_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if output.strip():
            # Store output for error reporting
            self._fastapi_stdout_buffer.append(output)
            
            # Write to log file
            if hasattr(self, '_fastapi_logger'):
                self._fastapi_logger.info(output.strip())
            
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
            # Store error for error reporting
            self._fastapi_stderr_buffer.append(error)
            
            # Check if this is actually an error or just uvicorn INFO messages
            # Uvicorn sends INFO messages to stderr, not stdout
            error_lower = error.lower()
            is_actual_error = any(keyword in error_lower for keyword in [
                'error', 'exception', 'traceback', 'failed', 'fatal', 'critical',
                'cannot', 'unable', 'failed to', 'error:', 'exception:'
            ])
            
            # Write to log file with appropriate level
            if hasattr(self, '_fastapi_logger'):
                if is_actual_error:
                    self._fastapi_logger.error(error.strip())
                else:
                    # Uvicorn INFO messages go to stderr, log as INFO
                    self._fastapi_logger.info(error.strip())
            
            # Only print as error if it's actually an error
            if is_actual_error:
                print(f"[NL FastAPI Server Error] {error.strip()}")
            else:
                print(f"[NL FastAPI Server Output] {error.strip()}")
            
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
                # Port is in use - try to free it and retry
                print("[NL Server Manager] Detected 'address already in use' for FastAPI server, attempting to free port 8000...")
                if self._check_and_free_port(8000):
                    print("[NL Server Manager] Port 8000 freed, retrying FastAPI server start...")
                    # Wait a moment, then retry
                    QTimer.singleShot(2000, lambda: self.start_fastapi_server(
                        self.fastapi_output_callback,
                        self.fastapi_error_callback
                    ))
                else:
                    # Could not free port, emit failure
                    self.fastapi_starting = False
                    self.fastapi_failed.emit(
                        "Port 8000 is in use and could not be freed. "
                        "Please stop other servers or free the port manually."
                    )
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
            # First, try to read any remaining output from process
            error_output = ""
            stdout_output = ""
            
            if self.fastapi_process:
                error_bytes = self.fastapi_process.readAllStandardError()
                if error_bytes:
                    error_output = bytes(error_bytes).decode('utf-8', errors='ignore')
                
                stdout_bytes = self.fastapi_process.readAllStandardOutput()
                if stdout_bytes:
                    stdout_output = bytes(stdout_bytes).decode('utf-8', errors='ignore')
            
            # Combine with buffered output (captured during process execution)
            if self._fastapi_stderr_buffer:
                buffered_errors = '\n'.join(self._fastapi_stderr_buffer)
                error_output = (buffered_errors + '\n' + error_output).strip()
            
            if self._fastapi_stdout_buffer:
                buffered_stdout = '\n'.join(self._fastapi_stdout_buffer)
                stdout_output = (buffered_stdout + '\n' + stdout_output).strip()
            
            print(f"\n\n[NL Server Manager] FastAPI server exited with code {exit_code}")
            
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
                    # Show the actual error output (truncate if too long)
                    error_msg = combined_output[:2000]  # Increased limit for better debugging
                    if len(combined_output) > 2000:
                        error_msg += f"\n\n... (truncated, {len(combined_output)} chars total)"
                    self.fastapi_failed.emit(f"Server exited with code {exit_code}:\n\n{error_msg}")
            else:
                # No output captured - this might indicate a very early crash
                # Check process error string for more info
                process_error = ""
                if self.fastapi_process:
                    process_error = self.fastapi_process.errorString()
                
                if process_error and process_error != "Unknown error":
                    self.fastapi_failed.emit(
                        f"Server exited with code {exit_code}.\n"
                        f"Process error: {process_error}\n\n"
                        f"No output captured - server may have crashed immediately on startup.\n"
                        f"Check:\n"
                        f"  - Python executable: {sys.executable}\n"
                        f"  - Server script exists: {self.nl_sql_dir / 'start_server.py'}\n"
                        f"  - Required packages installed (fastapi, uvicorn, openai)"
                    )
                else:
                    self.fastapi_failed.emit(
                        f"Server exited with code {exit_code} (no error output captured).\n\n"
                        f"Server may have crashed immediately on startup.\n"
                        f"Check server logs or try running manually:\n"
                        f"  python3 {self.nl_sql_dir / 'start_server.py'}"
                    )
    
    def _verify_fastapi_ready(self):
        """
        Verify that FastAPI server is ready and responding.
        
        Checks the /docs endpoint to confirm server is running.
        """
        import requests
        try:
            response = requests.get("http://localhost:8000/docs", timeout=2)
            if response.status_code == 200:
                print("\n\n[NL Server Manager] FastAPI server is ready")
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
        if hasattr(self, '_mcp_logger'):
            self._mcp_logger.info("\n\n" + "=" * 80)
            self._mcp_logger.info("MCP server process STARTED successfully")
            self._mcp_logger.info(f"Process PID: {self.mcp_process.processId() if self.mcp_process else 'Unknown'}")
            self._mcp_logger.info(f"Process state: {self.mcp_process.state() if self.mcp_process else 'Unknown'}")
        print("\n\n[NL Server Manager] MCP server process started")
        self.mcp_started.emit()
    
    def _on_mcp_output(self):
        """Handle MCP server stdout output."""
        if not self.mcp_process:
            return
        
        output = bytes(self.mcp_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        if output.strip():
            # Store output for error reporting
            self._mcp_stdout_buffer.append(output)
            
            # Write to log file
            if hasattr(self, '_mcp_logger'):
                self._mcp_logger.info(output.strip())
            
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
            # Store error for error reporting
            self._mcp_stderr_buffer.append(error)
            
            # Write to log file
            if hasattr(self, '_mcp_logger'):
                self._mcp_logger.error(error.strip())
            
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
                # Port is in use - try to free it and retry
                print("[NL Server Manager] Detected 'address already in use' for MCP server, attempting to free port 8001...")
                if self._check_and_free_port(8001):
                    print("[NL Server Manager] Port 8001 freed, retrying MCP server start...")
                    # Wait a moment, then retry
                    QTimer.singleShot(2000, lambda: self.start_mcp_server(
                        self.mcp_output_callback,
                        self.mcp_error_callback
                    ))
                else:
                    # Could not free port, emit failure
                    self.mcp_starting = False
                    self.mcp_failed.emit(
                        "Port 8001 is in use and could not be freed. "
                        "Please stop other servers or free the port manually."
                    )
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
            # First, try to read any remaining output from process
            error_output = ""
            stdout_output = ""
            
            if self.mcp_process:
                error_bytes = self.mcp_process.readAllStandardError()
                if error_bytes:
                    error_output = bytes(error_bytes).decode('utf-8', errors='ignore')
                
                stdout_bytes = self.mcp_process.readAllStandardOutput()
                if stdout_bytes:
                    stdout_output = bytes(stdout_bytes).decode('utf-8', errors='ignore')
            
            # Combine with buffered output (captured during process execution)
            if self._mcp_stderr_buffer:
                buffered_errors = '\n'.join(self._mcp_stderr_buffer)
                error_output = (buffered_errors + '\n' + error_output).strip()
            
            if self._mcp_stdout_buffer:
                buffered_stdout = '\n'.join(self._mcp_stdout_buffer)
                stdout_output = (buffered_stdout + '\n' + stdout_output).strip()
            
            print(f"\n\n[NL Server Manager] MCP server exited with code {exit_code}")
            
            # Combine outputs for better error detection
            combined_output = (error_output + "\n" + stdout_output).strip()
            
            if combined_output:
                print(f"[NL Server Manager] MCP server error output:\n{combined_output}")
                
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
                    # Show the actual error output (truncate if too long)
                    error_msg = combined_output[:2000]  # Increased limit for better debugging
                    if len(combined_output) > 2000:
                        error_msg += f"\n\n... (truncated, {len(combined_output)} chars total)"
                    self.mcp_failed.emit(f"Server exited with code {exit_code}:\n\n{error_msg}")
            else:
                # No output captured - this might indicate a very early crash
                # Check process error string for more info
                process_error = ""
                if self.mcp_process:
                    process_error = self.mcp_process.errorString()
                
                if process_error and process_error != "Unknown error":
                    self.mcp_failed.emit(
                        f"Server exited with code {exit_code}.\n"
                        f"Process error: {process_error}\n\n"
                        f"No output captured - server may have crashed immediately on startup.\n"
                        f"Check:\n"
                        f"  - Python executable: {sys.executable}\n"
                        f"  - Server script exists: {self.nl_sql_dir / 'start_mcp_server.py'}\n"
                        f"  - Required packages installed (fastapi, uvicorn)"
                    )
                else:
                    self.mcp_failed.emit(
                        f"Server exited with code {exit_code} (no error output captured).\n\n"
                        f"Server may have crashed immediately on startup.\n"
                        f"Check server logs or try running manually:\n"
                        f"  python3 {self.nl_sql_dir / 'start_mcp_server.py'}"
                    )
    
    def _verify_mcp_ready(self):
        """
        Verify that MCP server is ready and responding.
        
        Checks the /health endpoint to confirm server is running.
        """
        import requests
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("\n\n[NL Server Manager] MCP server is ready")
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
