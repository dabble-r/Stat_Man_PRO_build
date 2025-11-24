# Stat Manager
- v1.1.1 BETA

A comprehensive baseball/softball league management application built with Python and PySide6.

## Features

- **League Management**: Track teams, players, and league statistics
- **Player Statistics**: Manage batting and pitching statistics
- **Data Persistence**: SQLite database with CSV export/import
- **Visualization**: Interactive charts and graphs
- **Modern UI**: Clean, responsive interface with custom themes

## Project Structure

```
stat_man_g/
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── LICENSE.md               # License information
├── build_exe.bat            # Build project in Windows (venv build)
├── build_exe_.sh            # Build project in Linux (no venv build)
├── build_exe_venv.sh        # Build project in Linux (venv build)
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
│   │   │
│   │   ├── dialogs/         # Dialog windows (modular BaseDialog system)
│   │   │   ├── base_dialog.py             # Base dialog class (all modular dialogs extend this)
│   │   │   ├── dialog_templates.py        # Template classes for dialog configurations
│   │   │   ├── template_configs.py        # Factory functions for dialog templates
│   │   │   ├── dialog_handlers.py         # Business logic handlers for dialogs
│   │   │   │
│   │   │   ├── update_offense.py          # Offense stat update dialog (BaseDialog)
│   │   │   ├── update_pitching.py         # Pitching stat update dialog (BaseDialog)
│   │   │   ├── update_admin.py            # Team admin/management dialog (BaseDialog)
│   │   │   ├── update_team_stats.py       # Team stats update dialog (BaseDialog)
│   │   │   ├── update_lineup.py           # Lineup management dialog (BaseDialog)
│   │   │   ├── update_positions.py        # Player positions dialog (BaseDialog)
│   │   │   ├── update_league.py           # League admin dialog (BaseDialog)
│   │   │   ├── remove.py                  # Remove entity dialog (BaseDialog)
│   │   │   ├── search_dialog.py           # Search dialog (BaseDialog)
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
│   │   └── graph_window.py  # Graph display window
│   │
│   ├── utils/               # Utility functions
│   │   ├── file_dialog.py   # File/folder selection dialogs
│   │   ├── image.py         # Image and icon utilities
│   │   ├── refresh.py       # View refresh utilities
│   │   ├── undo.py          # Undo functionality
│   │   ├── tree_event_filter.py  # Tree widget event filtering
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
├── tests/                   # Unit tests
│   └── ...                  # Test files
│
├── Documentation/           # Additional documentation
├── archive/                 # Archived/deprecated code
└── myenv/                   # Virtual environment (git-ignored)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

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

# 3. Create dialog class
class MyDialog(BaseDialog):
    def __init__(self, league, selected, message, parent=None):
        template = create_my_dialog_template(
            update_handler=my_dialog_update_handler,
            undo_handler=my_dialog_undo_handler
        )
        context = {
            'league': league,
            'selected': selected,
            'message': message
        }
        super().__init__(template, context, parent=parent)
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

## Future Enhancements

- User authentication system
- Multi-league support
- Advanced statistical analysis
- Web-based interface
- Mobile companion app

---

For questions or support, please open an issue on the repository.

