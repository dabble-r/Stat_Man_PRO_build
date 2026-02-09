"""
Global Server Manager for persistent NL-to-SQL servers.

Manages server lifecycle across dialog instances, ensuring servers remain running
when the dialog is closed and can be reused when reopened.
"""

from typing import Optional
from PySide6.QtCore import QObject, Signal
from src.utils.nl_sql_server import NLServerManager
import logging

logger = logging.getLogger(__name__)


class GlobalServerManager(QObject):
    """
    Singleton-like manager for NL-to-SQL servers that persists across dialog instances.
    
    This ensures servers remain running when the dialog is closed and can be
    reused when the dialog is reopened.
    """
    
    # Singleton instance
    _instance: Optional['GlobalServerManager'] = None
    
    # Signals for server status updates
    servers_started = Signal()  # Servers started successfully
    servers_stopped = Signal()  # Servers stopped
    servers_ready = Signal()  # Both servers are ready
    fastapi_status_changed = Signal(bool)  # FastAPI server status (True=running)
    mcp_status_changed = Signal(bool)  # MCP server status (True=running)
    
    def __init__(self, parent=None):
        """Initialize Global Server Manager."""
        if GlobalServerManager._instance is not None:
            raise RuntimeError("GlobalServerManager is a singleton. Use get_instance() instead.")
        
        super().__init__(parent)
        self._server_manager: Optional[NLServerManager] = None
        self._api_key: Optional[str] = None
        self._is_running = False
        
        # Connect to server manager signals when created
        self._setup_server_signals()
    
    @classmethod
    def get_instance(cls, parent=None) -> 'GlobalServerManager':
        """
        Get singleton instance of GlobalServerManager.
        
        Args:
            parent: Optional parent QObject
            
        Returns:
            GlobalServerManager instance
        """
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance
    
    def _setup_server_signals(self):
        """Setup signal connections when server manager is created."""
        if self._server_manager:
            self._server_manager.all_servers_ready.connect(self._on_servers_ready)
            self._server_manager.fastapi_ready.connect(lambda: self.fastapi_status_changed.emit(True))
            self._server_manager.mcp_ready.connect(lambda: self.mcp_status_changed.emit(True))
            self._server_manager.fastapi_failed.connect(lambda msg: self.fastapi_status_changed.emit(False))
            self._server_manager.mcp_failed.connect(lambda msg: self.mcp_status_changed.emit(False))
    
    def _on_servers_ready(self):
        """Handle all servers ready signal."""
        self._is_running = True
        self.servers_ready.emit()
        logger.info("[GlobalServerManager] All servers are ready")
    
    def get_server_manager(self) -> Optional[NLServerManager]:
        """
        Get the current server manager instance.
        
        Returns:
            NLServerManager instance if it exists (even if servers are still starting), None otherwise
        """
        return self._server_manager
    
    def is_servers_running(self) -> bool:
        """
        Check if servers are currently running.
        
        Returns:
            True if both servers are running, False otherwise
        """
        if not self._server_manager:
            return False
        
        return (
            self._server_manager.is_fastapi_running() and
            self._server_manager.is_mcp_running()
        )
    
    def start_servers(self, api_key: str, parent=None) -> bool:
        """
        Start servers with the given API key.
        
        Args:
            api_key: OpenAI API key
            parent: Optional parent QObject for server manager
            
        Returns:
            True if servers started successfully, False otherwise
        """
        try:
            logger.info("=" * 80)
            logger.info(f"[GlobalServerManager] start_servers() called - {api_key[:7]}...{api_key[-4:] if len(api_key) > 11 else ''}")
            
            # If servers are already running, don't restart
            if self.is_servers_running():
                logger.info("[GlobalServerManager] Servers already running, reusing existing instance")
                return True
            
            # Store API key
            self._api_key = api_key
            logger.info(f"[GlobalServerManager] API key stored (length: {len(api_key)})")
            
            # Create server manager if needed
            if not self._server_manager:
                logger.info("[GlobalServerManager] Creating new NLServerManager instance")
                self._server_manager = NLServerManager(parent=parent)
                self._setup_server_signals()
                logger.info("[GlobalServerManager] NLServerManager instance created")
            else:
                logger.info("[GlobalServerManager] Reusing existing NLServerManager instance")
            
            # Set API key in environment
            import os
            os.environ['OPENAI_API_KEY'] = api_key
            logger.info(f"[GlobalServerManager] OPENAI_API_KEY set in environment (length: {len(api_key)})")
            
            # Start servers
            logger.info("[GlobalServerManager] Starting FastAPI server...")
            self._server_manager.start_fastapi_server()
            logger.info("[GlobalServerManager] Starting MCP server...")
            self._server_manager.start_mcp_server()
            
            logger.info("[GlobalServerManager] Server start commands issued (servers starting asynchronously)")
            return True
        except Exception as e:
            logger.error(f"[GlobalServerManager] Failed to start servers: {e}", exc_info=True)
            return False
    
    def stop_servers(self) -> None:
        """Stop all servers."""
        if self._server_manager:
            self._server_manager.stop_all_servers()
            self._is_running = False
            self.servers_stopped.emit()
            logger.info("[GlobalServerManager] Servers stopped")
    
    def get_server_status(self) -> dict:
        """
        Get current server status.
        
        Returns:
            Dictionary with server status information
        """
        if not self._server_manager:
            return {
                "fastapi_running": False,
                "mcp_running": False,
                "both_ready": False,
                "has_api_key": self._api_key is not None
            }
        
        return {
            "fastapi_running": self._server_manager.is_fastapi_running(),
            "mcp_running": self._server_manager.is_mcp_running(),
            "both_ready": self.is_servers_running(),
            "has_api_key": self._api_key is not None
        }
    
    def get_api_key(self) -> Optional[str]:
        """
        Get the stored API key.
        
        Returns:
            API key if available, None otherwise
        """
        return self._api_key
