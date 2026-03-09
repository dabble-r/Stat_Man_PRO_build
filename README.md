# Stat Manager
- v2.1.0

A comprehensive baseball/softball league management application built with Python and PySide6, featuring **AI/LLM integration** for natural language database queries and chart generation.

## Features

- **League Management**: Track teams, players, and league statistics
- **Player Statistics**: Manage batting and pitching statistics
- **Data Persistence**: SQLite database with CSV export/import
- **Visualization**: Interactive charts and graphs
- **Modern UI**: Clean, responsive interface with custom themes
- **Natural Language to SQL (NL-to-SQL)**: Query your database using natural language
  - Enter questions in plain English (e.g., "Show me all players with batting average above 0.300")
  - AI-powered SQL generation using OpenAI
  - Review and edit generated SQL before execution
  - Execute queries and view results in an interactive table
  - Requires OpenAI API key
- **NL-plot (natural language to chart)**: Generate charts from query results using natural language
  - After running a query, describe the chart you want (e.g., "bar chart of wins by team")
  - LLM generates chart configuration or plotting code; results displayed as PNG in-app
  - Uses the same OpenAI API key as NL-to-SQL

## Project Structure

```
stat_man_g/
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── LICENSE.md               # License information
├── stat_man_g.spec          # PyInstaller spec (Windows and Linux builds)
├── build_exe.bat            # Build Windows executable (run on Windows only; uses winenv)
├── build_exe.sh             # Build Linux executable (system Python)
├── build_exe_venv.sh        # Build Linux executable (venv build)
│
├── nl_sql/                  # NL-to-SQL and NL-plot server infrastructure
│   ├── __init__.py          # Package marker
│   ├── api_call.py          # FastAPI server (port 8000) - NL-to-SQL, NL-plot endpoints
│   ├── mcp_server.py        # MCP server (port 8001) - Database operations
│   ├── start_server.py      # FastAPI server startup script
│   ├── start_mcp_server.py  # MCP server startup script
│   └── run_plot_worker.py   # NL-plot code execution worker
│
├── src/                     # Main source code
│   ├── core/                # Core business logic
│   │   ├── league.py   # League data structure (uses Python list internally)
│   │   ├── team.py          # Team class with stat calculations
│   │   ├── player.py        # Player and Pitcher classes with stat logic
│   │   ├── node.py          # Stack node implementation (for undo functionality)
│   │   ├── game.py          # Game object and logic
│   │   └── stack.py         # Stack data structure for undo/redo
│   │
│   ├── ui/                  # User interface components
│   │   ├── main_window.py   # Main application window
│   │   ├── context/         # Shared application context (signals/slots)
│   │   │   ├── __init__.py
│   │   │   └── app_context.py  # AppContext QObject (league, selected, stack, undo, message, etc.; selection_changed, league_updated signals)
│   │   │
│   │   ├── dialogs/         # Dialog windows (modular BaseDialog system)
│   │   │   ├── base_dialog.py             # Base dialog class (all modular dialogs extend this)
│   │   │   ├── dialog_templates.py        # Template classes for dialog configurations
│   │   │   ├── template_configs.py        # Factory functions for dialog templates
│   │   │   ├── dialog_handlers.py         # Business logic handlers for dialogs
│   │   │   ├── nl_query_dialog.py        # NL-to-SQL query dialog (special case)
│   │   │   │
│   │   │   ├── update_offense.py          # Offense stat update dialog (BaseDialog)
│   │   │   ├── update_pitching.py         # Pitching stat update dialog (BaseDialog)
│   │   │   ├── update_admin.py            # Team admin/management dialog (BaseDialog)
│   │   │   ├── update_team_stats.py       # Team stats update dialog (BaseDialog)
│   │   │   ├── update_lineup.py           # Lineup management dialog (BaseDialog)
│   │   │   ├── update_positions.py        # Player positions dialog (BaseDialog)
│   │   │   ├── update_league.py           # League admin dialog (BaseDialog)
│   │   │   ├── remove.py                  # Remove entity dialog (BaseDialog)
│   │   │   ├── search_dialog.py           # Search dialog (BaseDialog) - includes NL query option
│   │   │   ├── bar_graph_dialog.py        # Bar graph selection dialog (BaseDialog)
│   │   │   ├── close.py                   # Application close confirmation (BaseDialog)
│   │   │   ├── update_theme_dialog.py     # Theme selection dialog (BaseDialog)
│   │   │   │
│   │   │   ├── update_dialog_ui.py        # Main update dialog hub (special case)
│   │   │   ├── new_player_ui.py           # Add new player dialog (special case)
│   │   │   ├── new_team_w_ui.py           # Add new team dialog (special case)
│   │   │   ├── add_save_ui.py             # Save/export dialog (special case)
│   │   │   ├── message.py                 # Custom message dialogs (utility)
│   │   │   └── stat_dialog_ui.py          # Player/team stat display (special case)
│   │   │
│   │   ├── views/           # Main view components (UI layer only)
│   │   │   ├── league_view_players.py     # Players and leaderboard view
│   │   │   ├── league_view_teams.py       # Teams W-L and AVG views
│   │   │   ├── leaderboard_ui.py          # Leaderboard widget
│   │   │   ├── selection.py               # Tree widget selection handler
│   │   │   └── tab_widget.py              # Custom tab widget
│   │   │
│   │   ├── logic/           # Business logic extracted from UI (NEW)
│   │   │   ├── dialogs/     # Dialog business logic
│   │   │   │   ├── update_offense_logic.py      # Offense stat update logic
│   │   │   │   ├── update_pitching_logic.py     # Pitching stat update logic
│   │   │   │   ├── update_admin_logic.py        # Admin update logic
│   │   │   │   ├── update_team_stats_logic.py   # Team stats update logic
│   │   │   │   ├── update_lineup_logic.py       # Lineup management logic
│   │   │   │   ├── update_dialog_logic.py       # Dialog helper logic
│   │   │   │   └── ...                         # Other dialog logic modules
│   │   │   │
│   │   │   ├── views/       # View business logic
│   │   │   │   ├── league_view_players_logic.py # Player view logic
│   │   │   │   └── league_view_teams_logic.py   # Team view logic
│   │   │   │
│   │   │   └── utils/       # UI utility logic
│   │   │       └── ...      # Utility logic functions
│   │   │
│   │   ├── widgets/         # Custom UI widgets
│   │   └── styles/          # Application styles and themes
│   │
│   ├── data/                # Data operations
│   │   ├── load/            # CSV loading functionality
│   │   │   ├── load_csv.py           # Main CSV import logic
│   │   │   ├── load_dialog_ui.py     # Load dialog UI
│   │   │   └── load.py               # Load utilities
│   │   │
│   │   ├── save/            # Database and CSV export
│   │   │   ├── save_manager.py       # Main save logic (DB + CSV)
│   │   │   ├── csv_export_handler.py # CSV export utilities
│   │   │   └── save_dialog.py        # Save dialog UI
│   │   │
│   │   └── database/        # Database utilities
│   │       └── ...          # DB initialization and schema
│   │
│   ├── visualization/       # Charts and graphs
│   │   ├── bar_graph.py     # Bar chart implementation
│   │   ├── donut_graph.py   # Donut chart implementation
│   │   ├── graph_window.py  # Graph display window
│   │   ├── nl_plot_pipeline.py  # NL-plot: LLM → chart config / plot code pipeline
│   │   └── viz_plot_builder.py  # Build figures from DataFrame and options
│   │
│   ├── utils/               # Utility functions
│   │   ├── file_dialog.py   # File/folder selection dialogs
│   │   ├── image.py         # Image and icon utilities
│   │   ├── refresh.py       # View refresh utilities
│   │   ├── undo.py          # Undo functionality
│   │   ├── tree_event_filter.py  # Tree widget event filtering
│   │   ├── nl_sql_server.py # NL-to-SQL server manager (starts/stops FastAPI and MCP servers)
│   │   ├── path_resolver.py # Path resolution for dev and bundled modes
│   │   └── ...              # Other utility modules
│   │
│   └── config/              # Configuration
│       └── ...              # App configuration files
│
├── data/                    # Runtime data
│   ├── database/            # SQLite database
│   │   └── League.db        # Main database file
│   ├── exports/             # CSV exports (timestamped folders)
│   │   └── save_*/          # Timestamped export folders
│   └── images/              # User-uploaded images/logos
│
├── assets/                  # Static assets
│   └── icons/               # Application icons
│
├── tests/                   # Unit tests and documentation
│   ├── slot_signal/         # AppContext/signals refactor plan and notes
│   │   ├── slot_signal_plan.md
│   │   ├── curr_view_search.md
│   │   └── fastapi_mcp_fail_after_context.md
│   ├── search/              # Search dialog behavior and column handling
│   │   └── dynamic_search_table_columns.md
│   ├── server_test.py       # NL-to-SQL server test script
│   └── *.md                 # Other test documentation and analysis files
│
├── Documentation/           # Additional documentation
├── archive/                 # Archived/deprecated code
├── GITHUB_AUTH_GUIDE.md     # GitHub authentication guide
└── myenv/                   # Virtual environment (git-ignored)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- **OpenAI API key** (required for NL-to-SQL and NL-plot; optional for the rest of the app)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd stat_man_g
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate  # On Linux/Mac
   # or
   myenv\Scripts\activate  # On Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   **Note**: NL-to-SQL and NL-plot require additional dependencies (included in `requirements.txt`):
   - `fastapi>=0.104.0` - Web framework for API server
   - `uvicorn` - ASGI server (e.g. `pip install uvicorn`)
   - `openai>=1.0.0` - OpenAI API client for SQL and chart generation
   - `sqlglot>=23.0.0` - SQL parsing and validation
   - `requests` - HTTP client
   - `matplotlib`, `seaborn` - Chart rendering for NL-plot

## Building standalone executables

The project builds **platform-specific** executables with PyInstaller. Use the build script for the OS where you will run the app; do not copy a Linux build to Windows or vice versa.

- **Windows**
  - Run **`build_exe.bat`** on Windows only. The script creates/uses a `winenv` virtual environment, installs dependencies, and runs PyInstaller using `stat_man_g.spec`. Output: `dist/stat_man_g.exe`.
  - On machines that run the exe (without Python), if you see "Missing dependency" or "DLL load failed", install the [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) (x64), then restart the app.
  - Optional: set `STATMANG_CONSOLE=1` before building to get a console window for debugging.
- **Linux**
  - Run **`build_exe.sh`** (system Python) or **`build_exe_venv.sh`** (venv). PyInstaller uses `stat_man_g.spec`; output is an ELF binary in `dist/`. Optional: install UPX for smaller binaries (`sudo apt-get install upx-ucl` on Debian/Ubuntu).

See also: `tests/servers/server_fail_11.md` (Windows build details), `tests/servers/server_fail_12.md` (Linux vs Windows server behavior).

## Usage

Run the application: (no print debug)
```bash
python3 main.py
```
Run the application: (with print debug)
```bash
STATMANG_DEBUG = 1 python3 main.py
```

### Key Features

#### League Management
- Create and manage teams
- Add players with detailed statistics
- Track wins, losses, and averages
- ![Alt text](/assets/screenshots/sm_launch1.jpg?raw=true "Launch League")


#### Data Import/Export
- **Load**: Import league data from CSV files
- **Save**: Export data to CSV or save to database
- Timestamp-based file organization
- ![Alt text](/assets/screenshots/sm_load2.jpg?raw=true "Save/Load")

#### Statistics Tracking
- Offensive statistics (batting average, hits, runs, etc.)
- Pitching statistics (ERA, strikeouts, wins, etc.)
- Team statistics and rankings

#### Visualization
- Team performance graphs
- Player stat breakdowns
- Interactive leaderboards
- ![Alt text](/assets/screenshots/teamGraph1.jpg?raw=true "Team Graph")
- ![Alt text](/assets/screenshots/playerGraph1.jpg?raw=true "Player Graph")

#### Natural Language to SQL Queries
- **Access**: Click "Search" button → Select "nl_query" radio option
- **Setup**: 
  1. Enter your OpenAI API key (required for SQL generation)
  2. Servers will start automatically (FastAPI on port 8000, MCP on port 8001)
  3. Wait for "Servers Ready" confirmation
- **Usage**:
  1. Enter a natural language query (e.g., "Show me all teams with wins greater than 5")
  2. Click "Submit NL Query" - SQL will be generated and displayed
  3. Review the generated SQL query (you can edit it if needed)
  4. Click "Execute SQL Query" to run the query on the database
  5. View results in the bottom-right panel
- **Features**:
  - AI-powered SQL generation using OpenAI GPT models
  - SQL validation and safety checks (SELECT only, LIMIT required)
  - Automatic schema detection from database
  - Results displayed in interactive table (DataFrame) with sort, export, and NL-plot visualization
  - NL-plot: describe a chart in natural language to generate a chart from current query results (same API key)
  - Dialog stays on top for easy access
- ![Alt text](/assets/screenshots/nl_query.jpg?raw=true "Natural Language Queries")

## Development

### Code Organization

The project follows a modular architecture with clear separation of concerns:

- **Core (`src/core/`)**: Core business logic independent of UI
  - Data structures (League using Python list, Stack with Node, Team, Player, Pitcher, Game)
  - Domain models (Team, Player, Pitcher, Game)
  - Stat calculation logic

- **UI (`src/ui/`)**: PySide6 interface components
  - **`dialogs/`**: Dialog windows (UI only, delegates to logic)
  - **`views/`**: Main view components (UI only, delegates to logic)
  - **`logic/`**: Business logic extracted from UI components
    - **`dialogs/`**: Dialog business logic (stat updates, validation)
    - **`views/`**: View business logic (leaderboard, sorting)
    - **`utils/`**: UI utility logic
  - **`widgets/`**: Custom UI widgets
  - **`styles/`**: Application themes and styling

- **Data (`src/data/`)**: Persistence layer
  - **`load/`**: CSV import and database loading
  - **`save/`**: Database writes and CSV export
  - **`database/`**: Database schema and utilities

- **Utils (`src/utils/`)**: Shared utility functions
  - File dialogs, image handling, undo/redo, refresh logic

- **Context (`src/ui/context/`)**: Shared application context
  - **`AppContext`** (QObject): Holds league, selected, leaderboard, lv_teams, stack, undo, message, file_dir, styles. Emits `selection_changed` and `league_updated`. Dialogs and views take `(context: AppContext, parent=None)` instead of 6–10 positional arguments.

- **Visualization (`src/visualization/`)**: Chart and graph components

### Architecture Pattern: UI/Logic Separation

The project follows a **separation of concerns** pattern where UI components delegate business logic to dedicated logic modules:

- **UI Files** (`src/ui/dialogs/`, `src/ui/views/`): Handle UI rendering, user input, and widget management only
- **Logic Files** (`src/ui/logic/dialogs/`, `src/ui/logic/views/`): Contain business logic, validation, calculations, and data transformations

**Example Pattern:**
```python
# In src/ui/dialogs/update_offense.py (UI layer)
from src.ui.logic.dialogs.update_offense_logic import logic_set_new_stat_player

def update_stats(self):
    # UI validation and user interaction
    val = int(self.int_input.text())
    # Delegate to logic layer
    logic_set_new_stat_player(stat, val, player, enable_callback=self.enable_buttons)
```

This separation allows:
- **Testability**: Logic can be tested independently of UI
- **Reusability**: Logic functions can be reused across different UI contexts
- **Maintainability**: Changes to UI or logic don't affect each other

### AppContext and signals/slots (slot_signal refactor)

To reduce long argument lists and centralize shared state, the UI uses a single **AppContext** (PySide6 `QObject`) created in the main window and passed into dialogs and views:

- **`src/ui/context/app_context.py`**: Defines **AppContext** with properties: `league`, `selected`, `leaderboard`, `lv_teams`, `lv_players`, `stack`, `undo`, `message`, `file_dir`, `styles`. Signals: **`selection_changed`**, **`league_updated`**. Method **`to_dict()`** builds the dict expected by BaseDialog’s template context.
- **Main window** creates the AppContext, wires league/selected/stack/undo/message/file_dir and the two views (`LeagueViewTeams`, `LeagueViewPlayers`), then passes **one** `context` into UpdateDialog, SearchDialog, RemoveDialog, and the stat dialog. When selection or league changes, the main window (or view) updates `context.selected` / `context.league` and emits the corresponding signal.
- **Dialogs and views** that previously took 6–10 arguments now take **`(context: AppContext, parent=None)`**. They call `context.to_dict()` (and optionally set `self.context = context`) before `super().__init__(template, context_dict, parent)`. Update sub-dialogs (offense, pitching, admin, team stats, lineup, positions, league) and others (remove, search, bar graph, stat dialog) follow this pattern.
- **Logic handlers** in `dialog_handlers.py` and in `src/ui/logic/dialogs/` take **`(dialog)`** (or `(context)` where applicable) and read `dialog.league`, `dialog.selected`, etc., instead of 5–8 separate parameters. This keeps handlers simple and avoids signature churn when new context fields are added.

Plan and notes: `tests/slot_signal/slot_signal_plan.md`, `tests/slot_signal/curr_view_search.md`, `tests/slot_signal/fastapi_mcp_fail_after_context.md`.

### Modular Dialog System

The application uses a **modular BaseDialog architecture** for consistent dialog creation and management:

#### Core Components

1. **`base_dialog.py`**: Base class that provides common dialog functionality
   - Handles layout management (standard, vertical, custom)
   - Manages input fields, radio buttons, checkboxes, and custom widgets
   - Provides validation and error handling
   - Supports custom widgets (date pickers, combo boxes, tree widgets)

2. **`dialog_templates.py`**: Template classes that define dialog structure
   - `StatUpdateTemplate`: For stat update dialogs (offense, pitching, team stats)
   - `AdminUpdateTemplate`: For admin/management dialogs
   - `SelectionTemplate`: For selection-based dialogs (lineup, positions)
   - `ConfirmationTemplate`: For confirmation dialogs
   - `SearchTemplate`: For search dialogs with tree results
   - `CheckboxSelectionTemplate`: For multi-select dialogs

3. **`template_configs.py`**: Factory functions that create configured templates
   - Pre-configured templates for each dialog type
   - Handles option lists, validators, and default values
   - Connects templates to appropriate handlers

4. **`dialog_handlers.py`**: Business logic handlers for dialog actions
   - Update handlers: Process form submissions
   - Undo handlers: Handle undo operations
   - View handlers: Display stats or additional information
   - Validation and enablement logic

#### Architecture Flow

```
Application Code
    ↓
Individual Dialog Classes (update_offense.py, etc.)
    ↓
BaseDialog (base_dialog.py) - UI structure and widget management
    ↓
Template Config (template_configs.py) - Pre-configured templates
    ↓
Template Classes (dialog_templates.py) - Template definitions
    ↓
Handlers (dialog_handlers.py) - Business logic
```

#### Benefits

- **Consistency**: All dialogs follow the same structure and behavior
- **Maintainability**: Changes to BaseDialog affect all dialogs automatically
- **Extensibility**: New dialogs can be created by configuring templates
- **Reduced Code Duplication**: Common functionality is centralized
- **Type Safety**: Template system ensures correct configuration

#### Example: Creating a New Dialog

```python
# 1. Create template configuration in template_configs.py
def create_my_dialog_template(update_handler, undo_handler):
    return StatUpdateTemplate.create_template(
        title="My Dialog",
        stat_options=["option1", "option2"],
        default_stat="option1",
        update_handler=update_handler,
        undo_handler=undo_handler
    )

# 2. Create handler in dialog_handlers.py
def my_dialog_update_handler(dialog):
    stat = dialog.get_selected_option('stat_selection')
    value = dialog.get_input_value('input')
    # Process update...

# 3. Create dialog class (caller passes AppContext from main window or parent dialog)
class MyDialog(BaseDialog):
    def __init__(self, context: AppContext, parent=None):
        template = create_my_dialog_template(
            update_handler=my_dialog_update_handler,
            undo_handler=my_dialog_undo_handler
        )
        # Build context dict for BaseDialog from AppContext
        super().__init__(template, context.to_dict(), parent=parent)
        self.context = context  # optional: store for sub-dialogs or handlers
```

#### Special Case Dialogs

Some dialogs don't use BaseDialog due to unique requirements:
- `message.py`: Utility dialog for notifications
- `stat_dialog_ui.py`: Complex display dialog with charts
- `update_dialog_ui.py`: Hub dialog that opens other dialogs
- `new_player_ui.py` / `new_team_w_ui.py`: Complex form dialogs

### Import Convention

Use absolute imports from the `src` package:
```python
from src.core.team import Team
from src.ui.dialogs.new_player_ui import AddPlayerDialog
from src.ui.logic.dialogs.update_offense_logic import logic_set_new_stat_player
from src.data.load.load_csv import load_all_csv_to_db
```

### Database Schema

The application uses SQLite with four main tables:
- `league`: League information and administrators
- `team`: Team data, roster, and statistics
- `player`: Player offensive statistics
- `pitcher`: Pitcher-specific statistics

### NL-to-SQL Architecture

The NL-to-SQL and NL-plot features use a two-server architecture (both require an OpenAI API key for SQL generation and chart generation):

1. **FastAPI Server (Port 8000)**:
   - Converts natural language to SQL using OpenAI
   - NL-plot: natural language chart description → chart config or plot code (LLM)
   - Validates generated SQL queries
   - Endpoints: `/nl_to_sql`, `/nl_to_chart_config`, `/nl_to_chart_png`, `/mcp/ask`, etc.
   - Requires OpenAI API key

2. **MCP Server (Port 8001)**:
   - Provides database schema and executes read-only SQL; runs NL-plot Python code and returns PNG.
   - Endpoints: `GET /health`, `GET /schema`, `GET /distinct_values`, `POST /execute`, `POST /run_plot`.
   - No API key required. See **MCP server details** below for full endpoint descriptions.

Both servers are managed by `NLServerManager`. When running from source they start as subprocesses; when running the **frozen** executable, behavior is platform-specific: on Windows the servers run in a separate process (QProcess) using system Python and the bundled `nl_sql` and `src` trees, while on Linux/macOS they may run in-process. They start automatically when you submit an API key in the NL query dialog and stop when the dialog is closed.

### MCP server details (port 8001)

The **MCP (Model Context Protocol) server** runs on port 8001 and handles all database access and plot execution for the NL-SQL and NL-plot features. It does **not** require an OpenAI API key. The FastAPI server (port 8000) calls the MCP server to get schema, run queries, and run NL-plot code.

| Endpoint | Method | Purpose |
|---------|--------|---------|
| `/health` | GET | Liveness check; returns `{"status": "ok"}`. |
| `/schema` | GET | Returns the SQLite database schema (table and column definitions) for LLM prompts. Response: `{"schema": "table_name(col1 type, ...)\n..."}`. |
| `/distinct_values` | GET | Query param: `column` (e.g. `positions`). Returns distinct values for that column so NL-to-SQL prompts can use exact DB values. Response: `{"values": ["..."]}`. |
| `/execute` | POST | Body: `{"sql": "SELECT ..."}`. Runs **read-only** SQL against `data/database/League.db`. Only `SELECT` is allowed; dangerous keywords (INSERT, UPDATE, DELETE, DROP, etc.) are rejected. Returns `{"success": true, "row_count": N, "results": [...]}`. |
| `/run_plot` | POST | Body: `{"code": "python code", "data": [list of dicts]}`. Executes LLM-generated Python plotting code (e.g. matplotlib) with `df` as a pandas DataFrame; returns PNG as base64. Used by the NL-plot “natural language to chart” flow. |

- **Database**: MCP uses the project database at `data/database/League.db` (or fallback from app path when bundled). Schema and execute both use this path.
- **Security**: `/execute` validates SQL (SELECT only, table names must exist). `/run_plot` runs code in a subprocess with a timeout (e.g. 30s).
- **Startup**: Started by `NLServerManager` together with the FastAPI server; see `nl_sql/start_mcp_server.py` and `src/utils/nl_sql_server.py`.

### Contributing

1. Create a new branch for your feature
2. Follow the existing code style
3. Update tests as needed
4. Submit a pull request

## License

See LICENSE.md for details.

## Notes

- Database is cleared on startup and shutdown (session-based)
- Images are stored as file paths in `data/images/`
- CSV exports include timestamps for version control
- The application supports multiple themes via the Styles module

## Troubleshooting

### Import Errors
If you encounter import errors after restructuring:
```bash
python update_imports.py
```

### Database Issues
If the database becomes corrupted:
```bash
rm data/database/League.db
```
The application will create a new database on next startup.

### Virtual Environment
If packages aren't found, ensure your virtual environment is activated:
```bash
source myenv/bin/activate  # Linux/Mac
```

## NL-to-SQL Feature Details

### How It Works

1. **User Input**: Enter a natural language question in the NL query dialog
2. **SQL Generation**: FastAPI server sends query to OpenAI with database schema
3. **SQL Validation**: Generated SQL is validated for safety (SELECT only, LIMIT required)
4. **User Review**: SQL is displayed for review and optional editing
5. **Execution**: User clicks "Execute SQL Query" to run on database
6. **Results**: Query results displayed in an interactive table (DataFrame) with sorting and export
7. **NL-plot (optional)**: From the same dialog, enter a natural-language chart description and click Submit to generate a chart from the current results via the LLM (e.g. bar, pie, line)

### Security Features

- Only SELECT queries allowed (no INSERT, UPDATE, DELETE, DROP, etc.)
- Automatic LIMIT clause addition (default 100 rows)
- SQL syntax validation using `sqlglot`
- Database path resolution with fallback to project root
- Table name verification before execution

### Requirements

- **OpenAI API Key**: Required for SQL generation
  - Get one at: https://platform.openai.com/api-keys
  - Token must have access to GPT models (gpt-4o-mini is default)
- **Internet Connection**: Required for OpenAI API calls
- **Database**: League.db must exist with proper schema

### Troubleshooting NL-to-SQL

**Servers won't start:**
- Check that ports 8000 and 8001 are available (on Windows they are not auto-freed; close the app using the port or run `netstat -ano | findstr :8000`).
- If Windows Firewall blocks the app, allow it for ports 8000/8001; ensure ports are not reserved (e.g. by Hyper-V).
- Verify OpenAI API key is valid.
- **Windows frozen exe:** If you see "Missing dependency" or "DLL load failed", install the [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) (x64), then restart the app.
- **Running from source on Windows:** Install Python from python.org (not the Store stub), add to PATH, or set `STATMANG_PYTHON_EXE` to the full path to `python.exe`.

**Building the Windows executable:**
- Build on Windows: run `build_exe.bat` (see **Building standalone executables** above). Do not copy a Linux `dist/` to Windows—the binary is platform-specific.

**SQL generation fails:**
- Verify API key has sufficient credits
- Check internet connection
- Ensure database schema is accessible

**"No such table" errors:**
- Verify database exists at `data/database/League.db`
- Check that tables are initialized (create a league first)
- Review database path resolution in server logs

**Query returns no results:**
- Verify database has data
- Check that SQL query is correct
- Review table names (use singular: `team`, `player`, not `teams`, `players`)

## Future Enhancements

- User authentication system
- Multi-league support
- Advanced statistical analysis
- Web-based interface
- Mobile companion app
- NL-plot presets and template charts

---

For questions or support, please open an issue on the repository.

