"""Create new stack screen."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, LoadingIndicator, TextArea

from portainer_tui.api.client import PortainerAPIError, PortainerClient

_COMPOSE_TEMPLATE = """\
services:
  app:
    image:
    restart: unless-stopped
    # ports:
    #   - "8080:80"
    # environment:
    #   - KEY=value
    # volumes:
    #   - ./data:/data
"""


class CreateStackScreen(Screen[bool]):
    """Full-screen editor for creating a new Portainer Compose stack.

    Dismisses with ``True`` if the stack was created, ``False`` otherwise.
    """

    DEFAULT_CSS = """
    CreateStackScreen {
        layout: vertical;
    }
    #create-bar {
        height: 3;
        background: $panel;
        layout: horizontal;
        padding: 0 1;
        align: left middle;
    }
    #create-name-label {
        width: auto;
        content-align: left middle;
        color: $text-muted;
        padding: 0 1 0 0;
    }
    #create-name-input {
        width: 30;
    }
    #create-hint {
        width: 1fr;
        content-align: right middle;
        color: $text-muted;
    }
    #create-textarea {
        height: 1fr;
    }
    #create-saving {
        display: none;
        align: center middle;
        height: 1fr;
        background: $background 80%;
    }
    #create-saving.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "create", "Create", show=True),
        Binding("escape", "close", "Close", show=True, priority=True),
    ]

    def __init__(self, client: PortainerClient, endpoint_id: int) -> None:
        super().__init__()
        self._client = client
        self._endpoint_id = endpoint_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="create-bar"):
            yield Label("Name:", id="create-name-label")
            yield Input(placeholder="my-stack", id="create-name-input")
            yield Label("ctrl+s create  •  esc close", id="create-hint")
        yield TextArea(
            _COMPOSE_TEMPLATE,
            language="yaml",
            id="create-textarea",
            tab_behavior="indent",
        )
        yield LoadingIndicator(id="create-saving")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "New Stack"
        self.query_one("#create-name-input", Input).focus()

    def action_create(self) -> None:
        self._do_create()

    @work(exclusive=True)
    async def _do_create(self) -> None:
        name = self.query_one("#create-name-input", Input).value.strip()
        if not name:
            self.notify("Stack name is required", severity="error")
            return
        content = self.query_one("#create-textarea", TextArea).text
        if not content.strip():
            self.notify("Compose content cannot be empty", severity="error")
            return
        self._set_saving(True)
        try:
            await self._client.create_stack(self._endpoint_id, name, content)
            self.notify(f"Stack '{name}' created", timeout=3)
            self.dismiss(True)
        except PortainerAPIError as e:
            self.notify(f"Create failed: {e}", severity="error")
        finally:
            self._set_saving(False)

    def action_close(self) -> None:
        self.dismiss(False)

    def _set_saving(self, saving: bool) -> None:
        indicator = self.query_one("#create-saving", LoadingIndicator)
        if saving:
            indicator.add_class("visible")
        else:
            indicator.remove_class("visible")
