"""Confirmation dialog widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmDialog(ModalScreen[bool]):
    """A modal confirmation dialog that returns True/False."""

    BINDINGS = [
        Binding("escape", "dismiss(False)", "Cancel", show=False),
        Binding("y", "confirm", "Yes", show=False),
        Binding("n", "dismiss(False)", "No", show=False),
    ]

    def __init__(self, message: str, title: str = "Confirm") -> None:
        super().__init__()
        self._message = message
        self._title = title

    def compose(self) -> ComposeResult:
        with self.prevent():
            from textual.containers import Vertical, Horizontal
            with Vertical(id="confirm-box"):
                yield Label(self._title, id="confirm-title")
                yield Label(self._message)
                with Horizontal(id="confirm-buttons"):
                    yield Button("No", id="confirm-no", variant="default")
                    yield Button("Yes", id="confirm-yes", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def action_confirm(self) -> None:
        self.dismiss(True)
