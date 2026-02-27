"""
NL-plot feature logging: path and logger for data/logs/nl_plot.log.
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.utils.path_resolver import get_app_base_path


def get_nl_plot_log_path() -> Path:
    """Return path to NL-plot log file (data/logs/nl_plot.log under app base)."""
    base = Path(get_app_base_path())
    log_dir = base / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "nl_plot.log"


_nl_plot_logger: logging.Logger | None = None


def get_nl_plot_logger() -> logging.Logger:
    """Return the NL-plot logger; configures FileHandler to nl_plot.log on first call."""
    global _nl_plot_logger
    if _nl_plot_logger is not None:
        return _nl_plot_logger
    _nl_plot_logger = logging.getLogger("nl_plot")
    _nl_plot_logger.setLevel(logging.DEBUG)
    _nl_plot_logger.handlers.clear()
    _nl_plot_logger.propagate = False
    try:
        log_path = get_nl_plot_log_path()
        handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        _nl_plot_logger.addHandler(handler)
    except Exception as e:
        _nl_plot_logger.addHandler(logging.NullHandler())
        _nl_plot_logger.debug("Could not create nl_plot log file: %s", e)
    return _nl_plot_logger
