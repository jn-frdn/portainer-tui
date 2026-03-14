"""JSON / text detail viewer widget."""

from __future__ import annotations

import json
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Label, Static
from textual.scroll_view import ScrollView


class DetailViewer(ScrollView):
    """Scrollable pane for displaying JSON or text detail."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
    ]

    DEFAULT_CSS = """
    DetailViewer {
        height: 1fr;
        background: $surface-darken-1;
        padding: 1 2;
        border-left: solid $panel;
    }
    """

    def __init__(self, data: Any, title: str = "Detail") -> None:
        super().__init__()
        self._title = title
        if isinstance(data, (dict, list)):
            self._text = json.dumps(data, indent=2, default=str)
        else:
            self._text = str(data)

    def compose(self) -> ComposeResult:
        yield Label(self._title, id="detail-title")
        yield Static(self._text, id="detail-content", markup=False)

    def action_close(self) -> None:
        self.remove()
