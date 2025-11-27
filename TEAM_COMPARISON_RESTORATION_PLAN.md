# Plan: Restore Team Comparison Bar Graph Functionality

## Current State Analysis

### Problem
When no item is selected, clicking the "Stat" button shows an error message and prevents the stat dialog from opening. However, the code for team comparison bar graphs already exists but is not accessible.

### Existing Code That Works

1. **`stat_dialog_ui.py`** - Already handles `selected=None` case:
   - **Line 117-118**: Returns "League Stats" label when `selected is None`
   - **Line 354-362**: Displays league admin stats in tree widget when `selected is None`
   - **Line 204-210**: `check_league()` method returns `'league'` when `selected is None` and teams exist
   - **Line 258-282**: `get_curr_league()` method exists and fully functional:
     - Opens `BarGraphDialog` for team selection
     - Retrieves selected teams
     - Generates bar graph comparing up to 5 teams (should be 6)
     - Displays graph in `graph_window`

2. **`bar_graph_dialog.py`** - Team selection dialog:
   - **Line 11**: Constructor accepts league, selected, message, styles, teams, parent
   - **Line 16**: Gets all team names from league
   - **Line 44**: `max_check = 5` (needs to be 6)
   - **Line 47-49**: Sets up checkbox change handlers
   - **Line 51-69**: `_check_on_change()` method enforces selection limit
   - **Line 60**: Error message says "Limit five teams per graph" (needs update)

3. **`bar_graph.py`** - Visualization:
   - **Line 145**: `assert len(team_names) <= 5` (needs to be 6)
   - **Line 139-262**: `BarGraph` class fully functional for displaying team comparisons

4. **`graph_window.py`** - Window container:
   - **Line 4-18**: `GraphWindow` class provides window container for graphs
   - Already used by `stat_dialog_ui.py` (line 85)

### Current Blocking Issue

**`main_window.py` lines 370-372**:
```python
if not self.selected or len(self.selected) == 0:
    self.message.show_message("No Selection: Please select a team or player to view stats.", btns_flag=False, timeout_ms=2000)
    return
```

This prevents the stat dialog from opening when nothing is selected, blocking access to the team comparison functionality.

### Code Locations Requiring Updates

1. **`src/ui/main_window.py`** (Line 367-377):
   - Remove or modify the early return when no selection
   - Allow `Ui_StatDialog` to open with `selected=None`

2. **`src/ui/dialogs/bar_graph_dialog.py`**:
   - **Line 44**: Change `self.max_check = 5` to `self.max_check = 6`
   - **Line 60**: Update error message from "Limit five teams per graph." to "Limit six teams per graph."

3. **`src/ui/dialogs/template_configs.py`** (Line 224):
   - Change `max_selections=5` to `max_selections=6`

4. **`src/visualization/bar_graph.py`** (Line 145):
   - Change `assert len(team_names) <= 5` to `assert len(team_names) <= 6`

## Implementation Plan

### Step 1: Enable Stat Dialog for No Selection
**File**: `src/ui/main_window.py`
**Location**: `setup_stat_ui()` method (lines 367-377)

**Change**: Remove the early return when no selection. Allow the stat dialog to open with `selected=None`.

**Current Code**:
```python
def setup_stat_ui(self):
    if not self.selected or len(self.selected) == 0:
        self.message.show_message("No Selection: Please select a team or player to view stats.", btns_flag=False, timeout_ms=2000)
        return
    
    self.stat_ui = Ui_StatDialog(self.league, self.message, self.selected, parent=self.stat_widget)
    self.stat_ui.get_stats(self.selected)
    self.stat_ui.exec()
```

**Proposed Code**:
```python
def setup_stat_ui(self):
    # Allow stat dialog to open even with no selection (for team comparison)
    self.stat_ui = Ui_StatDialog(self.league, self.message, self.selected, parent=self.stat_widget)
    self.stat_ui.get_stats(self.selected)
    self.stat_ui.exec()
```

### Step 2: Update Team Selection Limit to 6
**File**: `src/ui/dialogs/bar_graph_dialog.py`
**Changes**:
- **Line 44**: `self.max_check = 5` → `self.max_check = 6`
- **Line 60**: Update error message text

**Current Code**:
```python
self.max_check = 5
...
self.show_validation_error("Limit five teams per graph.")
```

**Proposed Code**:
```python
self.max_check = 6
...
self.show_validation_error("Limit six teams per graph.")
```

### Step 3: Update Template Configuration
**File**: `src/ui/dialogs/template_configs.py`
**Location**: `create_bar_graph_template()` function (line 224)

**Change**: `max_selections=5` → `max_selections=6`

### Step 4: Update Bar Graph Assertion
**File**: `src/visualization/bar_graph.py`
**Location**: `BarGraph.__init__()` method (line 145)

**Change**: `assert len(team_names) <= 5` → `assert len(team_names) <= 6`

## Expected Behavior After Implementation

1. **User clicks "Stat" button with no selection**:
   - Stat dialog opens showing "League Stats" label
   - Tree widget displays league admin statistics
   - "View Graph" button is visible and enabled

2. **User clicks "View Graph" button**:
   - `get_graph()` is called
   - `check_league()` returns `'league'` (if teams exist)
   - `get_curr_league()` is called
   - `BarGraphDialog` opens with checkboxes for all teams in league
   - User can select up to 6 teams
   - Error message appears if user tries to select more than 6 teams

3. **User selects teams and submits**:
   - Selected teams are stored in `teams_selected` list
   - Dialog closes
   - Bar graph window opens showing comparison of selected teams
   - Graph displays hits, SO, runs, ERA, K, and AVG for each selected team

## Testing Checklist

- [ ] Stat dialog opens when no item is selected
- [ ] League stats display correctly in tree widget when no selection
- [ ] "View Graph" button is visible and clickable
- [ ] Bar graph dialog opens with all teams as checkboxes
- [ ] User can select up to 6 teams
- [ ] Error message appears when trying to select 7th team
- [ ] Bar graph displays correctly with 1-6 teams selected
- [ ] Graph shows all 6 stats (hits, SO, runs, ERA, K, AVG) for each team
- [ ] Graph window is properly sized and displays correctly

## Additional Issue Found: Parameter Mismatch

**File**: `src/ui/dialogs/stat_dialog_ui.py` (Line 264)
**Issue**: Constructor call doesn't match signature

**Current Call**:
```python
self.graph_dialog = BarGraphDialog(self.league, self.selected, self.message, self.teams_selected, self)
```

**Constructor Signature** (line 11 of `bar_graph_dialog.py`):
```python
def __init__(self, league, selected, message, styles, teams, parent):
```

**Problem**: The call passes 5 arguments but the constructor expects 6. The `styles` parameter is missing, and `self.teams_selected` is being passed as the 4th argument (which maps to `styles`), but it should be the 5th argument (which maps to `teams`).

**Fix Option 1**: Remove unused `styles` parameter from `BarGraphDialog.__init__()`
**Fix Option 2**: Pass `None` for styles: `BarGraphDialog(self.league, self.selected, self.message, None, self.teams_selected, self)`

**Recommendation**: Remove the unused `styles` parameter from the constructor since it's not used anywhere in the class.

### Step 5: Fix BarGraphDialog Constructor Call
**File**: `src/ui/dialogs/bar_graph_dialog.py`
- Remove `styles` parameter from `__init__` signature (line 11)
- Update signature to: `def __init__(self, league, selected, message, teams, parent):`

**File**: `src/ui/dialogs/stat_dialog_ui.py`
- No change needed - current call will work after removing `styles` parameter

## Notes

- The existing code flow is already correct - we just need to remove the blocking check and update the team limit
- No changes needed to `stat_dialog_ui.py` logic - it already handles the `selected=None` case properly
- The `graph_window.py` is already properly integrated and needs no changes

