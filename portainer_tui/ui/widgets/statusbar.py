"""Bottom status bar widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class StatusBar(Widget):
    """Displays the current instance name, status message, and hint text."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel;
        layout: horizontal;
        padding: 0 1;
        dock: bottom;
    }
    #sb-left  { width: 1fr; content-align: left middle; }
    #sb-right { width: auto; content-align: right middle; color: $text-muted; }
    """

    status_text: reactive[str] = reactive("")

    def __init__(self, instance_name: str, hints: str = "") -> None:
        super().__init__()
        self._instance_name = instance_name
        self._hints = hints

    def compose(self) -> ComposeResult:
        yield Label("", id="sb-left")
        yield Label(self._hints, id="sb-right")

    def watch_status_text(self, value: str) -> None:
        instance_tag = f"[@click=''][bold cyan]{self._instance_name}[/]  "
        self.query_one("#sb-left", Label).update(instance_tag + value)

    def set_status(self, text: str) -> None:
        self.status_text = text
