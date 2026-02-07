"""
Search dialog using modular BaseDialog system.
"""
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.template_configs import create_search_template
from src.ui.dialogs.dialog_handlers import (
    search_submit_handler,
    search_view_handler,
    search_clear_handler
)
from typing import Union, Optional, Dict, Any
from src.core.player import Player
from src.core.team import Team
from PySide6.QtWidgets import (
    QTreeWidgetItem, QTreeWidget, QMessageBox, QInputDialog, QLineEdit, QTextEdit, 
    QSizePolicy, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal, QProcess, QTimer
import sys
import requests
import sqlite3
from pathlib import Path

# Add project root to path for imports
# search_dialog.py is at: src/ui/dialogs/search_dialog.py
# So we need to go up 4 levels: dialogs -> ui -> src -> project_root
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import NL server manager utility
from src.utils.nl_sql_server import NLServerManager


class SearchDialog(BaseDialog):
    """Dialog for searching teams or players."""
    
    def __init__(self, league, selected, stack, undo, message, parent=None):
        # Create template
        template = create_search_template(
            search_handler=search_submit_handler,
            view_handler=search_view_handler,
            clear_handler=search_clear_handler
        )
        
        # Create context
        context = {
            'league': league,
            'selected': None,  # Will be set when item is selected
            'leaderboard': None,
            'lv_teams': None,
            'stack': stack,
            'undo': undo,
            'message': message
        }
        
        # Initialize base dialog
        super().__init__(template, context, parent=parent)
        
        # Store search-specific state
        self.type = None
        
        # NL-to-SQL server management using utility
        self.nl_server_manager = NLServerManager(self)
        
        # Connect server manager signals
        self.nl_server_manager.fastapi_ready.connect(self._on_fastapi_ready)
        self.nl_server_manager.fastapi_failed.connect(self._on_fastapi_failed)
        self.nl_server_manager.mcp_ready.connect(self._on_mcp_ready)
        self.nl_server_manager.mcp_failed.connect(self._on_mcp_failed)
        self.nl_server_manager.all_servers_ready.connect(self._on_all_servers_ready)
        
        # Store pending query to execute once servers are ready
        self.pending_nl_query: Optional[str] = None
        self.pending_api_key: Optional[str] = None
        self.pending_sql_query: Optional[str] = None  # Store SQL for confirmation
        self.api_key_entered: bool = False  # Track if API key has been entered
        
        # Attach search population method
        self._populate_search = self._do_populate_search
        
        # Store original input field size for restoration
        self.original_input_size = None
        self.original_input_widget = None
        
        # SQL query display widget (created when NL query is submitted)
        self.sql_query_widget: Optional[QWidget] = None
        # Loading widget (shown while waiting for servers/SQL generation)
        self.loading_widget: Optional[QWidget] = None
        
        # Setup radio button toggle handler for nl_query
        self._setup_nl_query_toggle_handler()
    
    def get_input_value(self, key: str = 'input') -> str:
        """Override to handle both QLineEdit and QTextEdit."""
        if key in self.input_fields:
            input_widget = self.input_fields[key]
            if isinstance(input_widget, QTextEdit):
                return input_widget.toPlainText()
            else:
                return input_widget.text()
        return ''
    
    def _do_populate_search(self, selection: str, search_text: str):
        """Populate search tree with results."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        # Get search text if not provided
        if not search_text:
            search_text = self.get_input_value('input')
        
        if selection == "player":
            find_player = self.league.find_player(search_text)
            if find_player:
                self._dups_handler(find_player.name, player=find_player)
            else:
                self.show_validation_error("Player not found.")
                return
        
        elif selection == "team":
            find_team = self.league.find_team(search_text)
            if find_team:
                self._dups_handler(find_team.name, team=find_team)
            else:
                self.show_validation_error("Team not found.")
                return
        
        elif selection == "number":
            try:
                number = int(search_text)
            except ValueError:
                self.show_validation_error("Please enter a valid number.")
                return
            
            find_player_list = self.league.find_player_by_number(number)
            if len(find_player_list) > 0:
                self._dups_handler(find_player_list)
            else:
                self.show_validation_error("Player number not found.")
                return
        
        elif selection == "nl_query":
            # Handle natural language query
            # Don't clear input yet - preserve query text until SQL widget appears
            # The input will be cleared when SQL widget is created
            self._handle_nl_query(search_text)
            return  # Don't clear input field yet
    
    def _setup_nl_query_toggle_handler(self):
        """Setup toggle handler for nl_query radio button to resize input field."""
        if 'search_type' in self.radio_buttons:
            for radio in self.radio_buttons['search_type']:
                radio.toggled.connect(self._on_search_type_toggled)
    
    def _on_search_type_toggled(self, checked: bool):
        """Handle search type radio button toggle."""
        if not checked:
            return
        
        # Get the selected option
        selected = self.get_selected_option('search_type')
        
        # If nl_query is selected, prompt for API key first
        if selected == "nl_query":
            self._prompt_api_key_and_start_servers()
        
        # Get the input field
        if 'input' not in self.input_fields:
            return
        
        input_field = self.input_fields['input']
        
        if selected == "nl_query":
            # Store original widget if not already stored
            if self.original_input_widget is None:
                self.original_input_widget = input_field
                # Get original size
                original_size = input_field.size()
                self.original_input_size = (original_size.width(), original_size.height())
            
            # Convert QLineEdit to QTextEdit for multi-line input
            # Get current text and position
            current_text = input_field.text()
            parent = input_field.parent()
            layout = None
            layout_index = None
            
            # Find the layout containing this widget
            if hasattr(self, 'form_layout'):
                # Find which layout item contains this widget
                for i in range(self.form_layout.count()):
                    item = self.form_layout.itemAt(i)
                    if item and item.widget() == input_field:
                        layout = self.form_layout
                        layout_index = i
                        break
            
            if layout and layout_index is not None:
                # Remove old widget
                layout.removeWidget(input_field)
                input_field.deleteLater()
                
                # Create new QTextEdit
                text_edit = QTextEdit()
                text_edit.setPlainText(current_text)
                text_edit.setAlignment(input_field.alignment())
                if hasattr(input_field, 'placeholderText'):
                    text_edit.setPlaceholderText(input_field.placeholderText())
                
                # Set size: width=150px, height=50px, resizable
                text_edit.setMinimumSize(150, 50)
                text_edit.resize(150, 50)  # Set initial size
                text_edit.setMaximumSize(16777215, 16777215)  # Allow resizing
                text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                
                # Store in input_fields
                self.input_fields['input'] = text_edit
                
                # Add to layout at same position
                layout.insertWidget(layout_index, text_edit)
            else:
                # Fallback: just resize the existing QLineEdit
                input_field.setMinimumSize(150, 50)
                input_field.resize(150, 50)  # Set initial size
                input_field.setMaximumSize(16777215, 16777215)
                input_field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            # Restore original size for other options
            if isinstance(input_field, QTextEdit):
                # Convert back to QLineEdit
                current_text = input_field.toPlainText()
                parent = input_field.parent()
                layout = None
                layout_index = None
                
                # Find the layout
                if hasattr(self, 'form_layout'):
                    for i in range(self.form_layout.count()):
                        item = self.form_layout.itemAt(i)
                        if item and item.widget() == input_field:
                            layout = self.form_layout
                            layout_index = i
                            break
                
                if layout and layout_index is not None:
                    # Remove QTextEdit
                    layout.removeWidget(input_field)
                    input_field.deleteLater()
                    
                    # Create new QLineEdit
                    line_edit = QLineEdit()
                    line_edit.setText(current_text)
                    line_edit.setAlignment(Qt.AlignCenter)
                    
                    # Restore original size if available
                    if self.original_input_size:
                        line_edit.setMinimumSize(0, 0)
                        line_edit.setMaximumSize(16777215, 16777215)
                    
                    # Store in input_fields
                    self.input_fields['input'] = line_edit
                    
                    # Add to layout
                    layout.insertWidget(layout_index, line_edit)
            else:
                # Just restore size for QLineEdit
                if self.original_input_size:
                    input_field.setMinimumSize(0, 0)
                    input_field.setMaximumSize(16777215, 16777215)
    
    def _check_dups(self, target: str) -> bool:
        """Check if target already exists in search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return False
        
        for i in range(tree_widget.topLevelItemCount()):
            item = tree_widget.topLevelItem(i)
            if item.text(0) == target:
                return True
        return False
    
    def _permit_dups(self, target: Union[str, list]) -> Union[bool, None]:
        """Check and handle duplicates."""
        if isinstance(target, str) and self._check_dups(target):
            self.message.show_message(f"Search results for {target} already found.", btns_flag=True)
            if self.message.choice == "ok":
                return True
            elif self.message.choice == "no":
                return False
            else:
                return None
        elif isinstance(target, str) and not self._check_dups(target):
            return True
        elif isinstance(target, list):
            ret = []
            for el in target:
                if self._check_dups(el.name):
                    ret.append(el.name)
            if len(ret) > 0:
                self.message.show_message(f"Search results for\n {ret}\n already found.", btns_flag=True)
                if self.message.choice == "ok":
                    return True
                elif self.message.choice == "no":
                    return False
                elif self.message.choice == "cancel":
                    return None
            else:
                return True
        return True
    
    def _dups_handler(self, target: Union[str, list], player: Player = None, team: Team = None):
        """Handle duplicate checking and add items to tree."""
        ret = self._permit_dups(target)
        
        if ret == False:
            return False
        elif ret == None:
            tree_widget = self.get_custom_widget('search_tree')
            if tree_widget:
                tree_widget.clear()
                tree_widget.setVisible(False)
            self.resize(500, 350)
            return None
        elif ret == True:
            tree_widget = self.get_custom_widget('search_tree')
            if not tree_widget:
                return
            
            if player:
                self._add_item_player(player)
            elif team:
                self._add_item_team(team)
            elif isinstance(target, list):
                self._add_item_number(target)
    
    def _add_item_player(self, player: Player):
        """Add player to search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        tree_widget.setVisible(True)
        self.resize(500, 750)
        self.type = "player"
        
        player_name = player.name
        team = player.team.name
        avg = player.get_AVG()
        item = QTreeWidgetItem([player_name, team, str(avg)])
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setTextAlignment(1, Qt.AlignCenter)
        item.setTextAlignment(2, Qt.AlignCenter)
        # Ensure item is selectable and enabled
        item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        tree_widget.addTopLevelItem(item)
    
    def _add_item_team(self, team: Team):
        """Add team to search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        tree_widget.setVisible(True)
        self.resize(500, 750)
        self.type = "team"
        
        name = team.name
        avg = team.get_bat_avg()
        item = QTreeWidgetItem([name, str(avg)])
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setTextAlignment(1, Qt.AlignCenter)
        # Ensure item is selectable and enabled
        item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        tree_widget.addTopLevelItem(item)
    
    def _add_item_number(self, player_list: list):
        """Add multiple players to search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            return
        
        tree_widget.setVisible(True)
        self.resize(500, 750)
        self.type = "number"
        
        for el in player_list:
            player_name = el.name
            team = el.team.name
            avg = el.get_AVG()
            item = QTreeWidgetItem([player_name, team, str(avg)])
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            # Ensure item is selectable and enabled
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            tree_widget.addTopLevelItem(item)
    
    # ---------------------------------------------------------
    # NL-to-SQL Integration (Optional Feature)
    # ---------------------------------------------------------
    
    def _handle_nl_query(self, query_text: str):
        """Handle natural language query using NL-to-SQL feature."""
        # Check if API key is available
        if not self.pending_api_key or not self.api_key_entered:
            # API key not entered yet - prompt for it and start servers
            api_key = self._prompt_api_key_and_start_servers()
            if not api_key:
                # User cancelled API key entry
                return
        
        # Check if servers are ready
        if not self.nl_server_manager.are_all_servers_ready():
            # Servers not ready yet - store query and show loading widget
            self.pending_nl_query = query_text
            # Create loading widget to show query while waiting
            self._create_loading_widget(query_text)
            return
        
        # Store query for execution
        self.pending_nl_query = query_text
        
        # Execute query immediately since servers are ready
        self._execute_nl_query(query_text, self.pending_api_key)
    
    def _get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from user or settings."""
        # For now, prompt user - can be enhanced to use settings
        api_key, ok = QInputDialog.getText(
            self,
            "OpenAI API Key",
            "Enter your OpenAI API key:",
            echo=QLineEdit.EchoMode.Password
        )
        
        if ok and api_key:
            return api_key.strip()
        return None
    
    def _prompt_api_key_and_start_servers(self):
        """Prompt for API key when nl_query is selected, then start servers."""
        # Check if API key was already entered
        if self.api_key_entered and self.pending_api_key:
            # API key already entered, just start servers if not already running
            print("[SearchDialog] API key already entered, starting servers...")
            self._start_nl_servers_on_selection()
            return self.pending_api_key
        
        # Prompt for API key
        api_key = self._get_openai_api_key()
        if not api_key:
            # User cancelled - don't start servers
            print("[SearchDialog] API key entry cancelled")
            return None
        
        # Store API key
        self.pending_api_key = api_key
        self.api_key_entered = True
        print("[SearchDialog] API key entered, starting servers...")
        
        # Now start both servers
        self._start_nl_servers_on_selection()
        
        return api_key
    
    def _ensure_nl_servers_running(self):
        """Ensure NL-to-SQL servers are running and ready."""
        # Check if servers are already running
        fastapi_ready = False
        mcp_ready = False
        
        try:
            response = requests.get("http://localhost:8000/docs", timeout=1)
            if response.status_code == 200:
                fastapi_ready = True
        except:
            pass
        
        try:
            response = requests.get("http://localhost:8001/health", timeout=1)
            if response.status_code == 200:
                mcp_ready = True
        except:
            pass
        
        # Start servers if not running
        if not fastapi_ready:
            self.nl_server_manager.start_fastapi_server(
                output_callback=self._on_fastapi_output,
                error_callback=self._on_fastapi_error
            )
        
        if not mcp_ready:
            self.nl_server_manager.start_mcp_server(
                output_callback=self._on_mcp_output,
                error_callback=self._on_mcp_error
            )
        
        # If both are ready, execute query
        if fastapi_ready and mcp_ready:
            self._check_servers_and_execute()
        else:
            # Wait for servers to be ready
            # The ready signals will trigger _check_servers_and_execute
            pass
    
    def _on_fastapi_ready(self):
        """Called when FastAPI server is ready."""
        print("[SearchDialog] FastAPI server is ready")
        self._check_servers_and_execute()
    
    def _on_fastapi_failed(self, error_msg: str):
        """Called when FastAPI server fails to start."""
        print(f"[SearchDialog] FastAPI server failed: {error_msg}")
        # Don't show error immediately - check if server is actually running
        # Sometimes errors are false positives (e.g., warnings during startup)
        QTimer.singleShot(2000, lambda: self._verify_fastapi_after_error(error_msg))
    
    def _verify_fastapi_after_error(self, error_msg: str):
        """Verify if FastAPI server is actually running despite error message."""
        try:
            response = requests.get("http://localhost:8000/docs", timeout=2)
            if response.status_code == 200:
                print("[SearchDialog] FastAPI server is actually running despite error message")
                # Server is running, trigger ready check
                self._on_fastapi_ready()
                return
        except:
            pass
        # Server is actually not running, show error
        self.show_validation_error(f"FastAPI server failed to start:\n\n{error_msg}")
    
    def _on_mcp_ready(self):
        """Called when MCP server is ready."""
        print("[SearchDialog] MCP server is ready")
        self._check_servers_and_execute()
    
    def _on_mcp_failed(self, error_msg: str):
        """Called when MCP server fails to start."""
        print(f"[SearchDialog] MCP server failed: {error_msg}")
        # Don't show error immediately - check if server is actually running
        # Sometimes errors are false positives (e.g., warnings during startup)
        QTimer.singleShot(2000, lambda: self._verify_mcp_after_error(error_msg))
    
    def _verify_mcp_after_error(self, error_msg: str):
        """Verify if MCP server is actually running despite error message."""
        try:
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("[SearchDialog] MCP server is actually running despite error message")
                # Server is running, trigger ready check
                self._on_mcp_ready()
                return
        except:
            pass
        # Server is actually not running, show error
        self.show_validation_error(f"MCP server failed to start:\n\n{error_msg}")
    
    def _on_fastapi_output(self, output: str):
        """Handle FastAPI server output."""
        print(f"[SearchDialog FastAPI Output] {output.strip()}")
    
    def _on_fastapi_error(self, error: str):
        """Handle FastAPI server errors."""
        print(f"[SearchDialog FastAPI Error] {error.strip()}")
    
    def _on_mcp_output(self, output: str):
        """Handle MCP server output."""
        print(f"[SearchDialog MCP Output] {output.strip()}")
    
    def _on_mcp_error(self, error: str):
        """Handle MCP server errors."""
        print(f"[SearchDialog MCP Error] {error.strip()}")
    
    def _start_nl_servers_on_selection(self):
        """Start both NL-to-SQL servers when nl_query radio button is selected."""
        # Check if servers are already running
        fastapi_ready = False
        mcp_ready = False
        
        try:
            response = requests.get("http://localhost:8000/docs", timeout=1)
            if response.status_code == 200:
                fastapi_ready = True
        except:
            pass
        
        try:
            response = requests.get("http://localhost:8001/health", timeout=1)
            if response.status_code == 200:
                mcp_ready = True
        except:
            pass
        
        # Start servers if not already running
        if not fastapi_ready or not mcp_ready:
            print("[SearchDialog] Starting NL-to-SQL servers (nl_query selected)...")
            # Start FastAPI server with its callbacks
            if not fastapi_ready:
                self.nl_server_manager.start_fastapi_server(
                    output_callback=self._on_fastapi_output,
                    error_callback=self._on_fastapi_error
                )
            # Start MCP server with its callbacks
            if not mcp_ready:
                self.nl_server_manager.start_mcp_server(
                    output_callback=self._on_mcp_output,
                    error_callback=self._on_mcp_error
                )
        else:
            print("[SearchDialog] NL-to-SQL servers already running")
    
    def _on_all_servers_ready(self):
        """Called when both servers are ready."""
        print("[SearchDialog] All NL-to-SQL servers are ready")
        print(f"[SearchDialog] Checking for pending query: {self.pending_nl_query is not None}")
        print(f"[SearchDialog] Checking for API key: {self.pending_api_key is not None}")
        # If there's a pending query, execute it now
        if self.pending_nl_query and self.pending_api_key:
            print("[SearchDialog] Both query and API key present, executing...")
            self._check_servers_and_execute()
        else:
            print("[SearchDialog] Missing query or API key, cannot execute")
    
    # Old server management code removed - now using NLServerManager utility
    # All server management is handled by self.nl_server_manager
    
    def _check_servers_and_execute(self):
        """Check if both servers are ready and execute pending query."""
        print(f"[SearchDialog] _check_servers_and_execute called")
        print(f"[SearchDialog] pending_nl_query: {self.pending_nl_query is not None}")
        print(f"[SearchDialog] pending_api_key: {self.pending_api_key is not None}")
        
        # Check both servers
        fastapi_ready = False
        mcp_ready = False
        
        try:
            response = requests.get("http://localhost:8000/docs", timeout=1)
            if response.status_code == 200:
                fastapi_ready = True
                print("[NL Servers] FastAPI server is ready")
        except Exception as e:
            print(f"[NL Servers] FastAPI server not ready: {str(e)}")
        
        try:
            response = requests.get("http://localhost:8001/health", timeout=1)
            if response.status_code == 200:
                mcp_ready = True
                print("[NL Servers] MCP server is ready")
        except Exception as e:
            print(f"[NL Servers] MCP server not ready: {str(e)}")
        
        print(f"[SearchDialog] fastapi_ready: {fastapi_ready}, mcp_ready: {mcp_ready}")
        
        # If both servers are ready and we have a pending query, execute it
        if fastapi_ready and mcp_ready and self.pending_nl_query and self.pending_api_key:
            print("[NL Servers] Both servers ready, executing query...")
            query_text = self.pending_nl_query
            api_key = self.pending_api_key
            # Update loading widget to show "Generating SQL..."
            if self.loading_widget:
                # Update loading message
                for child in self.loading_widget.findChildren(QLabel):
                    if "Waiting for servers" in child.text():
                        child.setText("Generating SQL query from your natural language request...")
            
            # Execute the query - this will call the LLM
            self._execute_nl_query(query_text, api_key)
        elif not fastapi_ready or not mcp_ready:
            # Still waiting for servers, check again (with max retry limit)
            if not hasattr(self, '_server_check_count'):
                self._server_check_count = 0
            self._server_check_count += 1
            
            if self._server_check_count > 30:  # Max 60 seconds (30 * 2 seconds)
                self._server_check_count = 0
                self.show_validation_error(
                    "Servers failed to start within timeout period.\n\n"
                    "Please check:\n"
                    "1. Required packages are installed (fastapi, uvicorn, openai)\n"
                    "2. Ports 8000 and 8001 are not in use\n"
                    "3. Check console for error messages"
                )
                return
            
            print(f"[NL Servers] Waiting for servers... (attempt {self._server_check_count}/30)")
            QTimer.singleShot(2000, self._check_servers_and_execute)
        else:
            # Reset counter if we have no pending query
            self._server_check_count = 0
    
    def _check_mcp_and_execute(self):
        """Check MCP server and execute if both ready."""
        self._check_servers_and_execute()
    
    def _execute_nl_query(self, query_text: str, api_key: str):
        """Execute natural language query and display results."""
        from src.utils.path_resolver import get_database_path
        
        print(f"[SearchDialog] _execute_nl_query called with query: {query_text[:50]}...")
        print(f"[SearchDialog] API key present: {bool(api_key)}")
        
        # Update loading widget to show "Calling LLM..."
        if self.loading_widget:
            # Update loading message
            for child in self.loading_widget.findChildren(QLabel):
                if "Generating SQL" in child.text() or "Waiting for servers" in child.text():
                    child.setText("Calling LLM to generate SQL query...")
        
        try:
            # Get database name from path
            db_path = get_database_path()
            db_name = db_path.stem.lower()  # e.g., "league" from "League.db"
            
            print(f"[SearchDialog] Database: {db_name}, Path: {db_path}")
            
            # Make request to NL-to-SQL endpoint
            payload = {
                "provider": "OpenAI",
                "api_key": api_key,
                "database": db_name,
                "user_request": query_text
            }
            
            print(f"[SearchDialog] Sending POST request to http://localhost:8000/nl_to_sql")
            print(f"[SearchDialog] Payload: provider={payload['provider']}, database={payload['database']}, user_request length={len(payload['user_request'])}")
            
            response = requests.post(
                "http://localhost:8000/nl_to_sql",
                json=payload,
                timeout=30
            )
            
            print(f"[SearchDialog] Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                self.show_validation_error(f"Query failed: {error_detail}")
                return
            
            result = response.json()
            sql_query = result.get("sql_query", "")
            
            if not sql_query:
                self.show_validation_error("No SQL query generated.")
                return
            
            # Store SQL query for confirmation
            self.pending_sql_query = sql_query
            
            # Remove loading widget if present
            self._remove_loading_widget()
            
            # Create and show SQL query widget below text area
            self._create_sql_query_widget(sql_query, db_path)
            
        except requests.exceptions.ConnectionError:
            # Remove loading widget on error
            self._remove_loading_widget()
            self.show_validation_error(
                "Cannot connect to NL-to-SQL server. "
                "Please ensure the server is running on port 8000."
            )
        except Exception as e:
            # Remove loading widget on error
            self._remove_loading_widget()
            self.show_validation_error(f"Error executing query: {str(e)}")
    
    def _create_sql_query_widget(self, sql_query: str, db_path: Path):
        """Create a widget below text area to display SQL query with OK/Cancel buttons."""
        print(f"[SearchDialog] Creating SQL query widget for query: {sql_query[:50]}...")
        
        # Remove existing SQL query widget if present
        if self.sql_query_widget:
            print("[SearchDialog] Removing existing SQL query widget")
            if hasattr(self, 'form_layout'):
                # Find and remove from form_layout
                for i in range(self.form_layout.count()):
                    item = self.form_layout.itemAt(i)
                    if item and item.widget() == self.sql_query_widget:
                        self.form_layout.removeWidget(self.sql_query_widget)
                        break
            # Also try removing from parent if it exists
            if self.sql_query_widget.parent():
                self.sql_query_widget.setParent(None)
            self.sql_query_widget.deleteLater()
            self.sql_query_widget = None
        
        # Remove loading widget if present
        self._remove_loading_widget()
        
        # Clear input field now that we're creating the widget
        if 'input' in self.input_fields:
            input_widget = self.input_fields['input']
            if isinstance(input_widget, QTextEdit):
                input_widget.clear()
            else:
                input_widget.clear()
        
        # Create container widget
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f9f9f9;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # SQL Query Label
        sql_label = QLabel("Generated SQL Query:")
        sql_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(sql_label)
        
        # SQL Query Display (read-only text area) - formatted for database
        sql_display = QTextEdit()
        # Format SQL query for better readability
        formatted_sql = self._format_sql_query(sql_query)
        sql_display.setPlainText(formatted_sql)
        sql_display.setReadOnly(True)
        sql_display.setMaximumHeight(120)
        sql_display.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 2px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 5px;
            }
        """)
        layout.addWidget(sql_display)
        
        # Error/Success Message Area (initially hidden)
        error_label = QLabel()
        error_label.setVisible(False)
        error_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
        error_label.setWordWrap(True)
        layout.addWidget(error_label)
        
        # OK/Cancel Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        ok_button.clicked.connect(lambda: self._execute_sql_from_widget(sql_query, db_path, error_label))
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        cancel_button.clicked.connect(lambda: self._cancel_sql_execution())
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Store widget reference
        self.sql_query_widget = container
        self.sql_error_label = error_label
        
        # Add widget to layout below input field
        # In standard layout, form_layout is a QVBoxLayout inside form_widget
        # Find input field and add widget after it
        input_field = self.input_fields.get('input')
        if input_field and hasattr(self, 'form_layout'):
            # form_layout is QVBoxLayout, find input field position
            input_index = -1
            for i in range(self.form_layout.count()):
                item = self.form_layout.itemAt(i)
                if item and item.widget() == input_field:
                    input_index = i
                    break
            
            if input_index >= 0:
                # Add SQL widget after input field
                print(f"[SearchDialog] Adding SQL widget at index {input_index + 1} in form_layout")
                self.form_layout.insertWidget(input_index + 1, container)
            else:
                # Fallback: add at end
                print("[SearchDialog] Input field not found in form_layout, adding at end")
                self.form_layout.addWidget(container)
        elif hasattr(self, 'main_layout'):
            # Fallback to main_layout if form_layout not available
            print("[SearchDialog] Adding SQL widget to main_layout")
            # Find content_layout and add there
            if hasattr(self, 'content_layout'):
                self.content_layout.addWidget(container)
            else:
                self.main_layout.insertWidget(1, container)  # Insert after first stretch
        
        # Ensure widget is visible
        container.setVisible(True)
        container.show()
        
        # Resize dialog to accommodate new widget
        current_size = self.size()
        new_height = current_size.height() + 280
        self.resize(current_size.width(), new_height)
        
        print(f"[SearchDialog] SQL query widget created and added. Dialog resized to {current_size.width()}x{new_height}")
        
        # Force update to ensure widget is displayed
        self.update()
        container.update()
    
    def _create_loading_widget(self, query_text: str):
        """Create a loading widget to show the query while waiting for servers/SQL generation."""
        # Remove existing loading widget if present
        if self.loading_widget:
            if hasattr(self, 'form_layout'):
                for i in range(self.form_layout.count()):
                    item = self.form_layout.itemAt(i)
                    if item and item.widget() == self.loading_widget:
                        self.form_layout.removeWidget(self.loading_widget)
                        break
            if self.loading_widget.parent():
                self.loading_widget.setParent(None)
            self.loading_widget.deleteLater()
            self.loading_widget = None
        
        # Create loading widget
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                border: 1px solid #ffa500;
                border-radius: 4px;
                background-color: #fff8e1;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Status label
        status_label = QLabel("Processing your query...")
        status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #ff6f00;")
        layout.addWidget(status_label)
        
        # Query display (read-only)
        query_display = QTextEdit()
        query_display.setPlainText(query_text)
        query_display.setReadOnly(True)
        query_display.setMaximumHeight(80)
        query_display.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ffa500;
                border-radius: 2px;
                font-size: 11px;
                padding: 5px;
            }
        """)
        layout.addWidget(query_display)
        
        # Loading message
        loading_label = QLabel("Waiting for servers to start and generate SQL query...")
        loading_label.setStyleSheet("font-size: 10px; color: #666; font-style: italic;")
        layout.addWidget(loading_label)
        
        self.loading_widget = container
        
        # Add to layout (same approach as SQL widget)
        input_field = self.input_fields.get('input')
        widget_added = False
        
        if input_field and hasattr(self, 'form_layout'):
            input_index = -1
            for i in range(self.form_layout.count()):
                item = self.form_layout.itemAt(i)
                if item and item.widget() == input_field:
                    input_index = i
                    break
            
            if input_index >= 0:
                self.form_layout.insertWidget(input_index + 1, container)
                widget_added = True
            else:
                self.form_layout.addWidget(container)
                widget_added = True
        
        if not widget_added and hasattr(self, 'main_layout'):
            if hasattr(self, 'content_layout'):
                self.content_layout.addWidget(container)
            else:
                self.main_layout.insertWidget(1, container)
            widget_added = True
        
        if widget_added:
            container.setVisible(True)
            container.show()
            current_size = self.size()
            self.resize(current_size.width(), current_size.height() + 200)
            self.update()
    
    def _remove_loading_widget(self):
        """Remove the loading widget."""
        if self.loading_widget:
            if hasattr(self, 'form_layout'):
                for i in range(self.form_layout.count()):
                    item = self.form_layout.itemAt(i)
                    if item and item.widget() == self.loading_widget:
                        self.form_layout.removeWidget(self.loading_widget)
                        break
            if self.loading_widget.parent():
                self.loading_widget.setParent(None)
            self.loading_widget.deleteLater()
            self.loading_widget = None
    
    def _format_sql_query(self, sql_query: str) -> str:
        """Format SQL query for better readability."""
        # Basic SQL formatting - add line breaks after keywords
        formatted = sql_query.strip()
        # Add line breaks after major SQL keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 
                   'GROUP BY', 'ORDER BY', 'HAVING', 'UNION', 'INSERT', 'UPDATE', 'DELETE']
        for keyword in keywords:
            formatted = formatted.replace(f' {keyword} ', f'\n{keyword} ')
            formatted = formatted.replace(f' {keyword.lower()} ', f'\n{keyword} ')
        return formatted
    
    def _cancel_sql_execution(self):
        """Handle Cancel button click - do nothing, just clear pending query."""
        self.pending_nl_query = None
        print("[SearchDialog] SQL query execution cancelled by user")
    
    def _execute_sql_from_widget(self, sql_query: str, db_path: Path, 
                                  error_label: QLabel):
        """Execute SQL query and display results in a new window."""
        # Hide error label
        error_label.setVisible(False)
        error_label.clear()
        
        try:
            print(f"[SearchDialog] Executing SQL query: {sql_query}")
            print(f"[SearchDialog] Database path: {db_path}")
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            if not cursor.description:
                # Non-SELECT query
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                print(f"[SearchDialog] Query executed successfully. Rows affected: {affected}")
                
                # Show success message in error label (reusing it for success)
                error_label.setText(f"Query executed successfully. Rows affected: {affected}")
                error_label.setStyleSheet("color: green; font-weight: bold;")
                error_label.setVisible(True)
                self.pending_nl_query = None
                return
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            print(f"[SearchDialog] Query returned {len(rows)} rows with columns: {columns}")
            
            conn.close()
            
            # Create new window with tree widget to display results
            self._create_results_window(columns, rows, sql_query)
            
            # Clear pending query
            self.pending_nl_query = None
            
        except sqlite3.Error as e:
            print(f"[SearchDialog] SQL Error: {str(e)}")
            error_label.setText(f"SQL Error: {str(e)}")
            error_label.setStyleSheet("color: red; font-weight: bold;")
            error_label.setVisible(True)
        except Exception as e:
            print(f"[SearchDialog] Error executing SQL: {str(e)}")
            import traceback
            traceback.print_exc()
            error_label.setText(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red; font-weight: bold;")
            error_label.setVisible(True)
    
    def _create_results_window(self, columns: list, rows: list, sql_query: str):
        """Create a new window with tree widget to display query results."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
        
        # Create new dialog window
        results_dialog = QDialog(self)
        results_dialog.setWindowTitle("Query Results")
        results_dialog.setModal(False)  # Non-modal so user can interact with main dialog
        results_dialog.resize(800, 600)
        
        # Create layout
        layout = QVBoxLayout(results_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Query label
        query_label = QLabel(f"SQL Query: {sql_query}")
        query_label.setStyleSheet("font-weight: bold; font-size: 11px; padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        query_label.setWordWrap(True)
        layout.addWidget(query_label)
        
        # Results label
        results_label = QLabel(f"Results: {len(rows)} row(s)")
        results_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(results_label)
        
        # Create tree widget
        tree_widget = QTreeWidget()
        tree_widget.setHeaderLabels(columns)
        tree_widget.setColumnCount(len(columns))
        tree_widget.setAlternatingRowColors(True)
        tree_widget.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Populate tree widget with results
        for row in rows:
            item = QTreeWidgetItem([str(val) if val is not None else "NULL" for val in row])
            for i in range(len(columns)):
                item.setTextAlignment(i, Qt.AlignCenter)
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            tree_widget.addTopLevelItem(item)
        
        # Resize columns to fit content
        for i in range(len(columns)):
            tree_widget.resizeColumnToContents(i)
        
        layout.addWidget(tree_widget)
        
        # Show the dialog
        results_dialog.show()
        print(f"[SearchDialog] Results window displayed with {len(rows)} rows")
    
    def _execute_sql_and_display(self, sql_query: str, db_path: Path):
        """Execute SQL query and display results in search tree."""
        tree_widget = self.get_custom_widget('search_tree')
        if not tree_widget:
            print("[SearchDialog] Error: search_tree widget not found")
            self.show_validation_error("Search tree widget not available.")
            return
        
        try:
            print(f"[SearchDialog] Executing SQL query: {sql_query}")
            print(f"[SearchDialog] Database path: {db_path}")
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            if not cursor.description:
                # Non-SELECT query
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                print(f"[SearchDialog] Query executed successfully. Rows affected: {affected}")
                self.show_validation_error(f"Query executed successfully. Rows affected: {affected}")
                return
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            print(f"[SearchDialog] Query returned {len(rows)} rows with columns: {columns}")
            
            # Setup tree widget
            tree_widget.clear()
            tree_widget.setHeaderLabels(columns)
            tree_widget.setColumnCount(len(columns))
            tree_widget.setVisible(True)
            
            # Resize dialog to show results
            self.resize(800, 600)
            self.type = "nl_query"
            
            # Add rows to tree
            for row in rows:
                item = QTreeWidgetItem([str(val) if val is not None else "NULL" for val in row])
                for i in range(len(columns)):
                    item.setTextAlignment(i, Qt.AlignCenter)
                item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                tree_widget.addTopLevelItem(item)
            
            conn.close()
            
            print(f"[SearchDialog] Successfully displayed {len(rows)} rows in search tree")
            
            # Show success message if no rows
            if len(rows) == 0:
                self.show_validation_error("Query executed successfully but returned no results.")
            
        except sqlite3.Error as e:
            print(f"[SearchDialog] SQL Error: {str(e)}")
            self.show_validation_error(f"SQL Error: {str(e)}")
        except Exception as e:
            print(f"[SearchDialog] Error executing SQL: {str(e)}")
            import traceback
            traceback.print_exc()
            self.show_validation_error(f"Error: {str(e)}")
    
    def closeEvent(self, event):
        """Handle dialog close event - stop servers."""
        if self.nl_server_manager:
            self.nl_server_manager.stop_all_servers()
        super().closeEvent(event)
