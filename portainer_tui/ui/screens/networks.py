"""Networks view widget."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import DataTable, Label, LoadingIndicator

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.network import Network
from portainer_tui.ui.widgets.confirm import ConfirmDialog


_SORTABLE_COLS = {"name", "driver", "scope"}


class NetworksView(Widget):
    """Lists all networks on the selected endpoint."""

    DEFAULT_CSS = """
    NetworksView { height: 1fr; }
    NetworksView DataTable { height: 1fr; }
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
        self._networks: list[Network] = []
        self._display_networks: list[Network] = []
        self._sort_col: str | None = None
        self._sort_rev: bool = False

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="networks-table", cursor_type="row")
        table.add_column("ID", key="id")
        table.add_column("Name", key="name")
        table.add_column("Driver", key="driver")
        table.add_column("Scope", key="scope")
        table.add_column("Subnets", key="subnets")
        table.add_column("Internal", key="internal")
        table.display = False
        yield table
        yield Label("", id="sort-label")
        yield Label("No networks found.", id="empty-label")

    def on_mount(self) -> None:
        self.action_refresh()

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        self._set_loading(True)
        try:
            self._networks = await self._client.list_networks(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
        finally:
            self._set_loading(False)

    def _get_sorted_networks(self) -> list[Network]:
        if self._sort_col is None:
            return list(self._networks)
        rev = self._sort_rev
        if self._sort_col == "name":
            return sorted(self._networks, key=lambda n: n.name.lower(), reverse=rev)
        if self._sort_col == "driver":
            return sorted(self._networks, key=lambda n: n.driver.lower(), reverse=rev)
        if self._sort_col == "scope":
            return sorted(self._networks, key=lambda n: n.scope.lower(), reverse=rev)
        return list(self._networks)

    def _populate_table(self) -> None:
        table = self.query_one("#networks-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._networks:
            table.display = False
            empty.display = True
            self._update_sort_label()
            return
        table.display = True
        empty.display = False
        self._display_networks = self._get_sorted_networks()
        for n in self._display_networks:
            table.add_row(
                n.short_id, n.name, n.driver, n.scope,
                ", ".join(n.subnets) or "—",
                "yes" if n.internal else "no",
                key=n.id,
            )
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

    def _selected_network(self) -> Network | None:
        table = self.query_one("#networks-table", DataTable)
        if table.cursor_row is None or not self._display_networks:
            return None
        try:
            return self._display_networks[table.cursor_row]
        except IndexError:
            return None

    @work(exclusive=False)
    async def action_inspect(self) -> None:
        n = self._selected_network()
        if not n:
            return
        try:
            detail = await self._client.inspect_network(self._endpoint_id, n.id)
            from portainer_tui.ui.screens.containers import DetailScreen
            await self.app.push_screen(DetailScreen(detail, title=f"Network — {n.name}"))
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    @work(exclusive=False)
    async def action_remove(self) -> None:
        n = self._selected_network()
        if not n:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(f"Remove network [bold]{n.name}[/]?", title="Remove Network")
        )
        if not confirmed:
            return
        try:
            await self._client.remove_network(self._endpoint_id, n.id)
            self.notify(f"Removed network {n.name}")
            self.action_refresh()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
