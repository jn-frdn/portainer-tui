"""Endpoints selection screen."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, LoadingIndicator

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.endpoint import Endpoint


class EndpointsScreen(Screen[Endpoint | None]):
    """Displays available Portainer endpoints and lets the user pick one."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "select", "Select"),
        Binding("escape,q", "dismiss(None)", "Back"),
    ]

    def __init__(self, client: PortainerClient) -> None:
        super().__init__()
        self._client = client
        self._endpoints: list[Endpoint] = []

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="endpoints-table", cursor_type="row")
        table.add_columns("ID", "Name", "Type", "URL", "Status")
        table.display = False
        yield table
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Select Endpoint"
        self.action_refresh()

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        self._set_loading(True)
        try:
            self._endpoints = await self._client.list_endpoints()
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
        finally:
            self._set_loading(False)

    def _populate_table(self) -> None:
        table = self.query_one("#endpoints-table", DataTable)
        table.clear()
        for ep in self._endpoints:
            status_str = "[green]up[/]" if ep.status == 1 else "[red]down[/]"
            table.add_row(
                str(ep.id), ep.name, ep.type_label, ep.url, status_str,
                key=str(ep.id),
            )
        table.display = True

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = loading

    def action_select(self) -> None:
        table = self.query_one("#endpoints-table", DataTable)
        if table.cursor_row is None or not self._endpoints:
            return
        try:
            self.dismiss(self._endpoints[table.cursor_row])
        except IndexError:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_select()
