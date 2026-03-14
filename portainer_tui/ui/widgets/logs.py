"""Log viewer widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog


class LogScreen(Screen):
    """Full-screen log viewer for a container."""

    BINDINGS = [
        Binding("q,escape", "app.pop_screen", "Close"),
        Binding("end", "scroll_end", "Scroll to end"),
    ]

    def __init__(self, container_name: str, log_text: str) -> None:
        super().__init__()
        self._container_name = container_name
        self._log_text = log_text

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield RichLog(highlight=True, markup=False, id="log-view")
        yield Footer()

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", RichLog)
        log_view.write(self._log_text)
        log_view.scroll_end(animate=False)

    def on_screen_resume(self) -> None:
        self.sub_title = f"Logs — {self._container_name}"

    def action_scroll_end(self) -> None:
        self.query_one("#log-view", RichLog).scroll_end(animate=True)
