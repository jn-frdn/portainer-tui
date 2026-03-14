"""Stacks view widget."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import DataTable, Label, LoadingIndicator

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.stack import Stack
from portainer_tui.ui.widgets.confirm import ConfirmDialog


class StacksView(Widget):
    """Lists all stacks for the selected endpoint."""

    DEFAULT_CSS = """
    StacksView { height: 1fr; }
    StacksView DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("e", "edit", "Edit"),
        Binding("p", "pull_restart", "Pull & Redeploy"),
        Binding("i", "inspect", "View file"),
        Binding("d", "remove", "Remove"),
    ]

    def __init__(self, client: PortainerClient, endpoint_id: int) -> None:
        super().__init__()
        self._client = client
        self._endpoint_id = endpoint_id
        self._stacks: list[Stack] = []

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="stacks-table", cursor_type="row")
        table.add_columns("ID", "Name", "Type", "Status", "Created by")
        table.display = False
        yield table
        yield Label("No stacks found.", id="empty-label")

    def on_mount(self) -> None:
        self.action_refresh()

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        self._set_loading(True)
        try:
            self._stacks = await self._client.list_stacks(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
        finally:
            self._set_loading(False)

    def _populate_table(self) -> None:
        table = self.query_one("#stacks-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._stacks:
            table.display = False
            empty.display = True
            return
        table.display = True
        empty.display = False
        for s in self._stacks:
            status_markup = (
                "[green]active[/]" if s.status_label == "active" else "[dim]inactive[/]"
            )
            table.add_row(
                str(s.id), s.name, s.type_label, status_markup, s.created_by,
                key=str(s.id),
            )

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = loading

    def _selected_stack(self) -> Stack | None:
        table = self.query_one("#stacks-table", DataTable)
        if table.cursor_row is None or not self._stacks:
            return None
        try:
            return self._stacks[table.cursor_row]
        except IndexError:
            return None

    @work(exclusive=False)
    async def action_edit(self) -> None:
        s = self._selected_stack()
        if not s:
            return
        try:
            content = await self._client.get_stack_file(s.id)
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
            return
        from portainer_tui.ui.screens.stack_editor import StackEditorScreen
        saved = await self.app.push_screen_wait(
            StackEditorScreen(self._client, s, self._endpoint_id, content)
        )
        if saved:
            self.action_refresh()

    @work(exclusive=False)
    async def action_pull_restart(self) -> None:
        s = self._selected_stack()
        if not s:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(
                f"Pull latest images and redeploy stack [bold]{s.name}[/]?\n\n"
                "Services will be briefly restarted.",
                title="Pull & Redeploy",
            )
        )
        if not confirmed:
            return
        try:
            self.notify(f"Pulling images and redeploying '{s.name}'…", timeout=15)
            await self._client.redeploy_stack(s.id, self._endpoint_id, pull_image=True)
            self.notify(f"Stack '{s.name}' redeployed with latest images", timeout=4)
            self.action_refresh()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    @work(exclusive=False)
    async def action_inspect(self) -> None:
        s = self._selected_stack()
        if not s:
            return
        try:
            content = await self._client.get_stack_file(s.id)
            from portainer_tui.ui.screens.containers import DetailScreen
            await self.app.push_screen(DetailScreen(content, title=f"Stack file — {s.name}"))
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    async def action_remove(self) -> None:
        s = self._selected_stack()
        if not s:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(f"Remove stack [bold]{s.name}[/]?", title="Remove Stack")
        )
        if not confirmed:
            return
        try:
            await self._client.remove_stack(s.id, self._endpoint_id)
            self.notify(f"Removed stack {s.name}")
            self.action_refresh()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
