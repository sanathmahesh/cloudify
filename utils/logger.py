"""Centralized logging with Rich formatting for the migration pipeline."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "agent": "bold magenta",
})

console = Console(theme=_THEME)

_configured = False


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    handler = RichHandler(
        console=console,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )
    _configured = True


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Return a named logger that renders through Rich."""
    _configure_root()
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger
