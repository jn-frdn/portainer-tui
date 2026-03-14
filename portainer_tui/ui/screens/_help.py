"""Help overlay screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Label


_BINDINGS_HELP = [
    ("1–5", "Switch to Containers / Stacks / Volumes / Networks / Images tab"),
    ("e", "Open endpoint picker"),
    ("r", "Refresh current view"),
    ("↑ / ↓  or  j / k", "Navigate list"),
    ("enter", "Select / open detail"),
    ("s", "Start container"),
    ("S", "Stop container"),
    ("R", "Restart container"),
    ("l", "View container logs"),
    ("i", "Inspect (JSON detail)"),
    ("d", "Remove selected resource"),
    ("?", "Toggle this help"),
    ("q / ctrl+c", "Quit"),
]


class HelpScreen(ModalScreen):
    """Keyboard shortcut reference overlay."""

    BINDINGS = [
        Binding("escape,q,?", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Label(" Portainer TUI — Keyboard Shortcuts ", id="help-title")
        table = DataTable(show_header=False, cursor_type="none", id="help-table")
        table.add_columns("Key", "Action")
        for key, desc in _BINDINGS_HELP:
            table.add_row(f"[bold cyan]{key}[/]", desc)
        yield table
        yield Footer()
