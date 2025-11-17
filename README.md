# Stat Manager
- v1.0.0 BETA

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
│   │   ├── linked_list.py   # League data structure (uses Python list internally)
│   │   ├── team.py          # Team class with stat calculations
│   │   ├── player.py        # Player and Pitcher classes with stat logic
│   │   ├── node.py          # Stack node implementation (for undo functionality)
│   │   ├── game.py          # Game object and logic
│   │   └── stack.py         # Stack data structure for undo/redo
│   │
│   ├── ui/                  # User interface components
│   │   ├── main_window.py   # Main application window
│   │   │
│   │   ├── dialogs/         # Dialog windows (UI layer only)
│   │   │   ├── update_offense.py          # Offense stat update dialog
│   │   │   ├── update_pitching.py         # Pitching stat update dialog
│   │   │   ├── update_admin.py            # Team admin/management dialog
│   │   │   ├── update_team_stats.py       # Team stats update dialog
│   │   │   ├── update_lineup.py           # Lineup management dialog
│   │   │   ├── update_positions.py        # Player positions dialog
│   │   │   ├── update_game.py             # Game update dialog
│   │   │   ├── update_league.py           # League admin dialog
│   │   │   ├── update_dialog_ui.py        # Main update dialog hub
│   │   │   ├── new_player_ui.py           # Add new player dialog
│   │   │   ├── new_team_w_ui.py           # Add new team dialog
│   │   │   ├── add_save_ui.py             # Save/export dialog
│   │   │   ├── remove.py                  # Remove entity dialog
│   │   │   ├── close.py                   # Application close confirmation
│   │   │   ├── message.py                 # Custom message dialogs
│   │   │   ├── stat_dialog_ui.py          # Player/team stat display
│   │   │   ├── bar_graph_dialog.py        # Bar graph selection dialog
│   │   │   └── update_theme_dialog.py     # Theme selection dialog
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
│   │   │   ├── save.py               # Main save logic (DB + CSV)
│   │   │   ├── save_exp.py           # CSV export utilities
│   │   │   └── save_dialog_ui.py     # Save dialog UI
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

