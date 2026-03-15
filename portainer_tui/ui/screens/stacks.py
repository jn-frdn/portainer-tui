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


_SORTABLE_COLS = {"id", "name", "type_label", "status_label"}


class StacksView(Widget):
    """Lists all stacks for the selected endpoint."""

    DEFAULT_CSS = """
    StacksView { height: 1fr; }
    StacksView DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("n", "new_stack", "New"),
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
        self._display_stacks: list[Stack] = []
        self._sort_col: str | None = None
        self._sort_rev: bool = False

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="stacks-table", cursor_type="row")
        table.add_column("ID", key="id")
        table.add_column("Name", key="name")
        table.add_column("Type", key="type_label")
        table.add_column("Status", key="status_label")
        table.add_column("Created by", key="created_by")
        table.display = False
        yield table
        yield Label("", id="sort-label")
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

    def _get_sorted_stacks(self) -> list[Stack]:
        if self._sort_col is None:
            return list(self._stacks)
        rev = self._sort_rev
        if self._sort_col == "id":
            return sorted(self._stacks, key=lambda s: s.id, reverse=rev)
        if self._sort_col == "name":
            return sorted(self._stacks, key=lambda s: s.name.lower(), reverse=rev)
        if self._sort_col == "type_label":
            return sorted(self._stacks, key=lambda s: s.type_label.lower(), reverse=rev)
        if self._sort_col == "status_label":
            return sorted(self._stacks, key=lambda s: s.status_label.lower(), reverse=rev)
        return list(self._stacks)

    def _populate_table(self) -> None:
        table = self.query_one("#stacks-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._stacks:
            table.display = False
            empty.display = True
            self._update_sort_label()
            return
        table.display = True
        empty.display = False
        self._display_stacks = self._get_sorted_stacks()
        for s in self._display_stacks:
            status_markup = (
                "[green]active[/]" if s.status_label == "active" else "[dim]inactive[/]"
            )
            table.add_row(
                str(s.id), s.name, s.type_label, status_markup, s.created_by,
                key=str(s.id),
            )
        self._update_sort_label()

    def _update_sort_label(self) -> None:
        label = self.query_one("#sort-label", Label)
        if self._sort_col is None:
            label.update("")
            return
        col_name = {"id": "ID", "name": "Name", "type_label": "Type", "status_label": "Status"}.get(
            self._sort_col, self._sort_col.capitalize()
        )
        arrow = "↓" if self._sort_rev else "↑"
        label.update(f"[dim]Sorted by:[/] {col_name} {arrow}")

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

    def _selected_stack(self) -> Stack | None:
        table = self.query_one("#stacks-table", DataTable)
        if table.cursor_row is None or not self._display_stacks:
            return None
        try:
            return self._display_stacks[table.cursor_row]
        except IndexError:
            return None

    @work(exclusive=False)
    async def action_new_stack(self) -> None:
        from portainer_tui.ui.screens.create_stack import CreateStackScreen
        created = await self.app.push_screen_wait(
            CreateStackScreen(self._client, self._endpoint_id)
        )
        if created:
            self.action_refresh()

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

    @work(exclusive=False)
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
