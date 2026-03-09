"""
Shared application context (QObject) for dialogs and views.
Reduces many-argument passing by holding league, selected, stack, undo, message, etc.,
and emitting selection_changed / league_updated when relevant.
"""
from typing import Any, Optional
from PySide6.QtCore import QObject, Signal


class AppContext(QObject):
    """
    Holds shared UI dependencies and emits signals when selection or league changes.
    Dialogs and views take (context, parent) instead of 6-10 positional arguments.
    """

    selection_changed = Signal(object)   # new selected (list or None)
    league_updated = Signal(object)      # league instance (optional, for refresh)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._league: Any = None
        self._selected: Any = None
        self._leaderboard: Any = None
        self._lv_teams: Any = None
        self._stack: Any = None
        self._undo: Any = None
        self._message: Any = None
        self._file_dir: Optional[str] = None
        self._styles: Any = None
        self._lv_players: Any = None

    @property
    def lv_players(self):
        return self._lv_players

    @lv_players.setter
    def lv_players(self, value):
        self._lv_players = value

    @property
    def league(self):
        return self._league

    @league.setter
    def league(self, value):
        self._league = value
        self.league_updated.emit(value)

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        self.selection_changed.emit(value)

    @property
    def leaderboard(self):
        return self._leaderboard

    @leaderboard.setter
    def leaderboard(self, value):
        self._leaderboard = value

    @property
    def lv_teams(self):
        return self._lv_teams

    @lv_teams.setter
    def lv_teams(self, value):
        self._lv_teams = value

    @property
    def stack(self):
        return self._stack

    @stack.setter
    def stack(self, value):
        self._stack = value

    @property
    def undo(self):
        return self._undo

    @undo.setter
    def undo(self, value):
        self._undo = value

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    @property
    def file_dir(self):
        return self._file_dir

    @file_dir.setter
    def file_dir(self, value):
        self._file_dir = value

    @property
    def styles(self):
        return self._styles

    @styles.setter
    def styles(self, value):
        self._styles = value

    def to_dict(self) -> dict:
        """Build dict suitable for BaseDialog context (template system)."""
        return {
            "league": self._league,
            "selected": self._selected,
            "leaderboard": self._leaderboard,
            "lv_teams": self._lv_teams,
            "lv_players": self._lv_players,
            "stack": self._stack,
            "undo": self._undo,
            "message": self._message,
        }

    @classmethod
    def from_dialog(cls, dialog) -> "AppContext":
        """Build a minimal context from a dialog that has .league, .message, .selected (e.g. BaseDialog)."""
        ctx = cls()
        ctx._league = getattr(dialog, "league", None)
        ctx._message = getattr(dialog, "message", None)
        ctx._selected = getattr(dialog, "selected", None)
        return ctx
