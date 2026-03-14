"""Volumes view widget."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import DataTable, Label, LoadingIndicator

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.volume import Volume
from portainer_tui.ui.widgets.confirm import ConfirmDialog


class VolumesView(Widget):
    """Lists all volumes on the selected endpoint."""

    DEFAULT_CSS = """
    VolumesView { height: 1fr; }
    VolumesView DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("i", "inspect", "Inspect"),
        Binding("d", "remove", "Remove"),
    ]

    def __init__(self, client: PortainerClient, endpoint_id: int) -> None:
        super().__init__()
        self._client = client
        self._endpoint_id = endpoint_id
        self._volumes: list[Volume] = []

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="volumes-table", cursor_type="row")
        table.add_columns("Name", "Driver", "Scope", "Mountpoint")
        table.display = False
        yield table
        yield Label("No volumes found.", id="empty-label")

    def on_mount(self) -> None:
        self.action_refresh()

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        self._set_loading(True)
        try:
            self._volumes = await self._client.list_volumes(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
        finally:
            self._set_loading(False)

    def _populate_table(self) -> None:
        table = self.query_one("#volumes-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._volumes:
            table.display = False
            empty.display = True
            return
        table.display = True
        empty.display = False
        for v in self._volumes:
            table.add_row(v.name, v.driver, v.scope, v.mountpoint, key=v.name)

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = loading

    def _selected_volume(self) -> Volume | None:
        table = self.query_one("#volumes-table", DataTable)
        if table.cursor_row is None or not self._volumes:
            return None
        try:
            return self._volumes[table.cursor_row]
        except IndexError:
            return None

    @work(exclusive=False)
    async def action_inspect(self) -> None:
        v = self._selected_volume()
        if not v:
            return
        try:
            detail = await self._client.inspect_volume(self._endpoint_id, v.name)
            from portainer_tui.ui.screens.containers import DetailScreen
            await self.app.push_screen(DetailScreen(detail, title=f"Volume — {v.name}"))
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    async def action_remove(self) -> None:
        v = self._selected_volume()
        if not v:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(f"Remove volume [bold]{v.name}[/]?", title="Remove Volume")
        )
        if not confirmed:
            return
        try:
            await self._client.remove_volume(self._endpoint_id, v.name)
            self.notify(f"Removed volume {v.name}")
            self.action_refresh()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
