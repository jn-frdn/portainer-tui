"""Containers view widget."""

from __future__ import annotations

import time

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

_SORTABLE_COLS = {"name", "image", "state", "stack", "age"}


def _age(ts: int) -> str:
    delta = int(time.time()) - ts
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"


class ContainersView(Widget):
    """Lists all containers on the selected endpoint."""

    DEFAULT_CSS = """
    ContainersView { height: 1fr; }
    ContainersView DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("e", "edit", "Edit"),
        Binding("p", "pull_restart", "Pull & Restart"),
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
        self._display_containers: list[Container] = []
        self._sort_col: str | None = None
        self._sort_rev: bool = False

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="containers-table", cursor_type="row")
        table.add_column("", key="state_icon")
        table.add_column("Name", key="name")
        table.add_column("Image", key="image", width=40)
        table.add_column("State", key="state")
        table.add_column("Stack", key="stack")
        table.add_column("Age", key="age")
        table.add_column("Status", key="status")
        table.add_column("Ports", key="ports")
        table.display = False
        yield table
        yield Label("", id="sort-label")
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

    def _get_sorted_containers(self) -> list[Container]:
        if self._sort_col is None:
            return list(self._containers)
        rev = self._sort_rev
        if self._sort_col == "name":
            return sorted(self._containers, key=lambda c: c.name.lower(), reverse=rev)
        if self._sort_col == "image":
            return sorted(self._containers, key=lambda c: c.image.lower(), reverse=rev)
        if self._sort_col == "state":
            return sorted(self._containers, key=lambda c: c.state.value, reverse=rev)
        if self._sort_col == "stack":
            return sorted(self._containers, key=lambda c: (c.stack_name or "").lower(), reverse=rev)
        if self._sort_col == "age":
            # ascending (↑) = youngest first = highest created timestamp first
            return sorted(self._containers, key=lambda c: c.created, reverse=not rev)
        return list(self._containers)

    def _populate_table(self) -> None:
        table = self.query_one("#containers-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._containers:
            table.display = False
            empty.display = True
            self._update_sort_label()
            return
        table.display = True
        empty.display = False
        self._display_containers = self._get_sorted_containers()
        for c in self._display_containers:
            table.add_row(
                _STATE_SYMBOLS.get(c.state, "?"),
                c.name,
                c.image,
                c.state.value,
                c.stack_name or "—",
                _age(c.created),
                c.status,
                c.port_summary,
                key=c.id,
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

    def _selected_container(self) -> Container | None:
        table = self.query_one("#containers-table", DataTable)
        if table.cursor_row is None or not self._display_containers:
            return None
        try:
            return self._display_containers[table.cursor_row]
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
    async def action_pull_restart(self) -> None:
        c = self._selected_container()
        if not c:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(
                f"Pull latest image for [bold]{c.name}[/] and recreate the container?\n\n"
                "The container will be briefly unavailable.",
                title="Pull & Restart",
            )
        )
        if not confirmed:
            return
        try:
            inspect_data = await self._client.inspect_container(self._endpoint_id, c.id)
            self.notify(f"Pulling {c.image}…", timeout=10)
            await self._client.pull_image(self._endpoint_id, c.image)
            self.notify("Image pulled — recreating container…", timeout=5)
            await self._do_recreate(c, inspect_data)
            self.notify(f"'{c.name}' restarted with latest image", timeout=4)
            self._containers = await self._client.list_containers(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    async def _do_recreate(self, c: Container, inspect_data: dict) -> None:
        """Stop → remove → create (same config) → start."""
        client = self._client
        eid = self._endpoint_id

        cfg = inspect_data.get("Config", {})
        host_cfg = inspect_data.get("HostConfig", {})
        networks = list((inspect_data.get("NetworkSettings", {}).get("Networks") or {}).keys())
        primary_net = networks[0] if networks else host_cfg.get("NetworkMode", "bridge")

        if c.state.value == "running":
            await client.stop_container(eid, c.id)
        await client.remove_container(eid, c.id, force=True)

        create_config: dict = {
            "Image": cfg.get("Image", c.image),
            "Cmd": cfg.get("Cmd"),
            "Entrypoint": cfg.get("Entrypoint"),
            "Env": cfg.get("Env"),
            "ExposedPorts": cfg.get("ExposedPorts", {}),
            "Labels": cfg.get("Labels", {}),
            "WorkingDir": cfg.get("WorkingDir", ""),
            "User": cfg.get("User", ""),
            "Volumes": cfg.get("Volumes"),
            "HostConfig": host_cfg,
            "NetworkingConfig": {"EndpointsConfig": {primary_net: {}}},
        }
        create_config = {k: v for k, v in create_config.items() if v is not None}

        net_mode = host_cfg.get("NetworkMode", "bridge")
        new_id = await client.create_container(eid, c.name, create_config)
        for net in networks:
            if net and net != net_mode:
                try:
                    await client.connect_network(eid, net, new_id)
                except PortainerAPIError:
                    pass
        await client.start_container(eid, new_id)

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
