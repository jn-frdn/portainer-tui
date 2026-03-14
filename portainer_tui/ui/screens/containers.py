"""Containers view widget."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Header, Label, LoadingIndicator

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.container import Container, ContainerState
from portainer_tui.ui.widgets.confirm import ConfirmDialog


_STATE_SYMBOLS = {
    ContainerState.RUNNING: "[green]●[/]",
    ContainerState.EXITED: "[red]●[/]",
    ContainerState.PAUSED: "[yellow]●[/]",
    ContainerState.RESTARTING: "[cyan]↻[/]",
    ContainerState.DEAD: "[red dim]✕[/]",
    ContainerState.CREATED: "[dim]○[/]",
    ContainerState.REMOVING: "[red dim]✕[/]",
    ContainerState.UNKNOWN: "[dim]?[/]",
}


class ContainersView(Widget):
    """Lists all containers on the selected endpoint."""

    DEFAULT_CSS = """
    ContainersView { height: 1fr; }
    ContainersView DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("e", "edit", "Edit"),
        Binding("s", "start", "Start"),
        Binding("S", "stop", "Stop"),
        Binding("R", "restart", "Restart"),
        Binding("l", "logs", "Logs"),
        Binding("i", "inspect", "Inspect"),
        Binding("d", "remove", "Remove"),
    ]

    def __init__(self, client: PortainerClient, endpoint_id: int) -> None:
        super().__init__()
        self._client = client
        self._endpoint_id = endpoint_id
        self._containers: list[Container] = []

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="containers-table", cursor_type="row")
        table.add_columns("", "Name", "Image", "State", "Status", "Ports")
        table.display = False
        yield table
        yield Label("No containers found.", id="empty-label")

    def on_mount(self) -> None:
        self.action_refresh()

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        self._set_loading(True)
        try:
            self._containers = await self._client.list_containers(self._endpoint_id)
            self._populate_table()
            self.notify("Containers refreshed", timeout=2)
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
        finally:
            self._set_loading(False)

    def _populate_table(self) -> None:
        table = self.query_one("#containers-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._containers:
            table.display = False
            empty.display = True
            return
        table.display = True
        empty.display = False
        for c in self._containers:
            table.add_row(
                _STATE_SYMBOLS.get(c.state, "?"),
                c.name,
                c.image,
                c.state.value,
                c.status,
                c.port_summary,
                key=c.id,
            )

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = loading

    def _selected_container(self) -> Container | None:
        table = self.query_one("#containers-table", DataTable)
        if table.cursor_row is None or not self._containers:
            return None
        try:
            return self._containers[table.cursor_row]
        except IndexError:
            return None

    @work(exclusive=False)
    async def action_edit(self) -> None:
        c = self._selected_container()
        if not c:
            return
        try:
            inspect_data = await self._client.inspect_container(self._endpoint_id, c.id)
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
            return
        from portainer_tui.ui.screens.container_editor import ContainerEditorScreen
        recreated = await self.app.push_screen_wait(
            ContainerEditorScreen(self._client, c, self._endpoint_id, inspect_data)
        )
        if recreated:
            self._containers = await self._client.list_containers(self._endpoint_id)
            self._populate_table()

    @work(exclusive=False)
    async def action_start(self) -> None:
        c = self._selected_container()
        if not c:
            return
        try:
            await self._client.start_container(self._endpoint_id, c.id)
            self.notify(f"Started {c.name}")
            self._containers = await self._client.list_containers(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    @work(exclusive=False)
    async def action_stop(self) -> None:
        c = self._selected_container()
        if not c:
            return
        try:
            await self._client.stop_container(self._endpoint_id, c.id)
            self.notify(f"Stopped {c.name}")
            self._containers = await self._client.list_containers(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    @work(exclusive=False)
    async def action_restart(self) -> None:
        c = self._selected_container()
        if not c:
            return
        try:
            await self._client.restart_container(self._endpoint_id, c.id)
            self.notify(f"Restarted {c.name}")
            self._containers = await self._client.list_containers(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    @work(exclusive=False)
    async def action_logs(self) -> None:
        c = self._selected_container()
        if not c:
            return
        try:
            log_text = await self._client.get_container_logs(self._endpoint_id, c.id)
            from portainer_tui.ui.widgets.logs import LogScreen
            await self.app.push_screen(LogScreen(c.name, log_text))
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    @work(exclusive=False)
    async def action_inspect(self) -> None:
        c = self._selected_container()
        if not c:
            return
        try:
            detail = await self._client.inspect_container(self._endpoint_id, c.id)
            await self.app.push_screen(DetailScreen(detail, title=f"Inspect — {c.name}"))
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    async def action_remove(self) -> None:
        c = self._selected_container()
        if not c:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(f"Remove container [bold]{c.name}[/]?", title="Remove Container")
        )
        if not confirmed:
            return
        try:
            await self._client.remove_container(self._endpoint_id, c.id, force=True)
            self.notify(f"Removed {c.name}")
            self._containers = await self._client.list_containers(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")


class DetailScreen(Screen):
    """Full-screen JSON / text detail viewer."""

    BINDINGS = [Binding("q,escape", "app.pop_screen", "Close")]

    def __init__(self, data: object, title: str = "Detail") -> None:
        super().__init__()
        self._data = data
        self._title = title

    def compose(self) -> ComposeResult:
        import json
        from textual.widgets import Footer, TextArea

        content = (
            json.dumps(self._data, indent=2, default=str)
            if isinstance(self._data, (dict, list))
            else str(self._data)
        )
        yield Header(show_clock=False)
        yield TextArea(content, read_only=True, id="detail-text")
        yield Footer()

    def on_mount(self) -> None:
        self.title = self._title
