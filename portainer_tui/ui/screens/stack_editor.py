"""Stack file editor screen."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, LoadingIndicator, TextArea

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.stack import Stack
from portainer_tui.ui.widgets.confirm import ConfirmDialog


class StackEditorScreen(Screen[bool]):
    """Full-screen editor for a Portainer stack file.

    Dismisses with ``True`` if the stack was saved, ``False`` otherwise.
    """

    DEFAULT_CSS = """
    StackEditorScreen {
        layout: vertical;
    }
    #editor-bar {
        height: 1;
        background: $panel;
        layout: horizontal;
        padding: 0 1;
        dock: top;
    }
    #editor-status {
        width: 1fr;
        content-align: left middle;
        color: $text-muted;
    }
    #editor-hint {
        width: auto;
        content-align: right middle;
        color: $text-muted;
    }
    #editor-modified {
        color: $warning;
        text-style: bold;
    }
    #editor-textarea {
        height: 1fr;
    }
    #editor-saving {
        display: none;
        align: center middle;
        height: 1fr;
        background: $background 80%;
    }
    #editor-saving.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("escape", "close", "Close", show=True, priority=True),
    ]

    _modified: reactive[bool] = reactive(False)

    def __init__(
        self,
        client: PortainerClient,
        stack: Stack,
        endpoint_id: int,
        initial_content: str,
    ) -> None:
        super().__init__()
        self._client = client
        self._stack = stack
        self._endpoint_id = endpoint_id
        self._initial_content = initial_content
        self._saved = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        # Info bar just below the header
        with self._bar_container():
            yield Label("", id="editor-status")
            yield Label("ctrl+s save  •  esc close", id="editor-hint")
        yield TextArea(
            self._initial_content,
            language="yaml",
            id="editor-textarea",
            tab_behavior="indent",
        )
        yield LoadingIndicator(id="editor-saving")
        yield Footer()

    def _bar_container(self):
        from textual.containers import Horizontal
        return Horizontal(id="editor-bar")

    def on_mount(self) -> None:
        self.title = f"Edit stack — {self._stack.name}"
        self._update_status()
        self.query_one("#editor-textarea", TextArea).focus()

    # ------------------------------------------------------------------
    # Dirty tracking
    # ------------------------------------------------------------------

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        current = event.text_area.text
        self._modified = current != self._initial_content
        self._update_status()

    def _update_status(self) -> None:
        status = self.query_one("#editor-status", Label)
        if self._modified:
            status.update("[bold yellow]● modified[/]  " + self._stack.name)
        else:
            status.update(f"[dim]●[/]  {self._stack.name}  [dim]({self._stack.type_label})[/]")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_save(self) -> None:
        self._do_save()

    @work(exclusive=True)
    async def _do_save(self) -> None:
        content = self.query_one("#editor-textarea", TextArea).text
        self._set_saving(True)
        try:
            await self._client.update_stack(
                self._stack.id,
                self._endpoint_id,
                stack_file_content=content,
            )
            self._initial_content = content
            self._modified = False
            self._update_status()
            self._saved = True
            self.notify(f"Stack '{self._stack.name}' saved", timeout=3)
        except PortainerAPIError as e:
            self.notify(f"Save failed: {e}", severity="error")
        finally:
            self._set_saving(False)

    async def action_close(self) -> None:
        if self._modified:
            confirmed = await self.app.push_screen_wait(
                ConfirmDialog(
                    "You have unsaved changes. Discard and close?",
                    title="Unsaved Changes",
                )
            )
            if not confirmed:
                return
        self.dismiss(self._saved)

    def _set_saving(self, saving: bool) -> None:
        indicator = self.query_one("#editor-saving", LoadingIndicator)
        if saving:
            indicator.add_class("visible")
        else:
            indicator.remove_class("visible")
