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


_SORTABLE_COLS = {"name", "driver", "scope"}

def _in_use_indicator(in_use: bool | None) -> str:
    if in_use is True:
        return "[green]●[/]"
    if in_use is False:
        return "[dim]○[/]"
    return "[dim]?[/]"


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
        Binding("D", "prune", "Delete Unused"),
    ]

    def __init__(self, client: PortainerClient, endpoint_id: int) -> None:
        super().__init__()
        self._client = client
        self._endpoint_id = endpoint_id
        self._volumes: list[Volume] = []
        self._display_volumes: list[Volume] = []
        self._sort_col: str | None = None
        self._sort_rev: bool = False

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="volumes-table", cursor_type="row")
        table.add_column("Name", key="name")
        table.add_column("In Use", key="in_use")
        table.add_column("Driver", key="driver")
        table.add_column("Scope", key="scope")
        table.add_column("Mountpoint", key="mountpoint")
        table.display = False
        yield table
        yield Label("", id="sort-label")
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

    def _get_sorted_volumes(self) -> list[Volume]:
        if self._sort_col is None:
            return list(self._volumes)
        rev = self._sort_rev
        if self._sort_col == "name":
            return sorted(self._volumes, key=lambda v: v.name.lower(), reverse=rev)
        if self._sort_col == "driver":
            return sorted(self._volumes, key=lambda v: v.driver.lower(), reverse=rev)
        if self._sort_col == "scope":
            return sorted(self._volumes, key=lambda v: v.scope.lower(), reverse=rev)
        return list(self._volumes)

    def _populate_table(self) -> None:
        table = self.query_one("#volumes-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._volumes:
            table.display = False
            empty.display = True
            self._update_sort_label()
            return
        table.display = True
        empty.display = False
        self._display_volumes = self._get_sorted_volumes()
        for v in self._display_volumes:
            table.add_row(v.name, _in_use_indicator(v.in_use), v.driver, v.scope, v.mountpoint, key=v.name)
        self._update_sort_label()

    def _update_sort_label(self) -> None:
        label = self.query_one("#sort-label", Label)
        if self._sort_col is None:
            label.update("")
            return
        arrow = "↓" if self._sort_rev else "↑"
        label.update(f"[dim]Sorted by:[/] {self._sort_col.capitalize()} {arrow}")

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        col = event.column_key.value
        if col not in _SORTABLE_COLS:
            return
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False
        self._populate_table()

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = loading

    def _selected_volume(self) -> Volume | None:
        table = self.query_one("#volumes-table", DataTable)
        if table.cursor_row is None or not self._display_volumes:
            return None
        try:
            return self._display_volumes[table.cursor_row]
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

    async def action_prune(self) -> None:
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog("Remove all unused volumes?", title="Prune Volumes")
        )
        if not confirmed:
            return
        try:
            result = await self._client.prune_volumes(self._endpoint_id)
            deleted = result.get("VolumesDeleted") or []
            self.notify(f"Pruned {len(deleted)} volume(s)")
            self.action_refresh()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
