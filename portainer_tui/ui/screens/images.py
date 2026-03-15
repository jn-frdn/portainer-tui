"""Images view widget."""

from __future__ import annotations

import time

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import DataTable, Label, LoadingIndicator

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.image import Image
from portainer_tui.ui.widgets.confirm import ConfirmDialog


_SORTABLE_COLS = {"tag", "size", "created"}


def _age(ts: int) -> str:
    delta = int(time.time()) - ts
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"


class ImagesView(Widget):
    """Lists all images on the selected endpoint."""

    DEFAULT_CSS = """
    ImagesView { height: 1fr; }
    ImagesView DataTable { height: 1fr; }
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
        self._images: list[Image] = []
        self._display_images: list[Image] = []
        self._sort_col: str | None = None
        self._sort_rev: bool = False

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="images-table", cursor_type="row")
        table.add_column("ID", key="id")
        table.add_column("Tag", key="tag", width=60)
        table.add_column("Size", key="size")
        table.add_column("Age", key="created")
        table.display = False
        yield table
        yield Label("", id="sort-label")
        yield Label("No images found.", id="empty-label")

    def on_mount(self) -> None:
        self.action_refresh()

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        self._set_loading(True)
        try:
            self._images = await self._client.list_images(self._endpoint_id)
            self._populate_table()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
        finally:
            self._set_loading(False)

    def _get_sorted_images(self) -> list[Image]:
        if self._sort_col is None:
            return list(self._images)
        rev = self._sort_rev
        if self._sort_col == "tag":
            return sorted(self._images, key=lambda img: img.tag.lower(), reverse=rev)
        if self._sort_col == "size":
            return sorted(self._images, key=lambda img: img.size, reverse=rev)
        if self._sort_col == "created":
            # ascending (↑) = youngest first = highest timestamp first
            return sorted(self._images, key=lambda img: img.created, reverse=not rev)
        return list(self._images)

    def _populate_table(self) -> None:
        table = self.query_one("#images-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._images:
            table.display = False
            empty.display = True
            self._update_sort_label()
            return
        table.display = True
        empty.display = False
        self._display_images = self._get_sorted_images()
        for img in self._display_images:
            table.add_row(img.short_id, img.tag, img.size_human, _age(img.created), key=img.id)
        self._update_sort_label()

    def _update_sort_label(self) -> None:
        label = self.query_one("#sort-label", Label)
        if self._sort_col is None:
            label.update("")
            return
        col_name = {"tag": "Tag", "size": "Size", "created": "Age"}.get(
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

    def _selected_image(self) -> Image | None:
        table = self.query_one("#images-table", DataTable)
        if table.cursor_row is None or not self._display_images:
            return None
        try:
            return self._display_images[table.cursor_row]
        except IndexError:
            return None

    @work(exclusive=False)
    async def action_inspect(self) -> None:
        img = self._selected_image()
        if not img:
            return
        try:
            detail = await self._client.inspect_image(self._endpoint_id, img.id)
            from portainer_tui.ui.screens.containers import DetailScreen
            await self.app.push_screen(DetailScreen(detail, title=f"Image — {img.tag}"))
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")

    async def action_remove(self) -> None:
        img = self._selected_image()
        if not img:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(f"Remove image [bold]{img.tag}[/]?", title="Remove Image")
        )
        if not confirmed:
            return
        try:
            await self._client.remove_image(self._endpoint_id, img.id)
            self.notify(f"Removed image {img.tag}")
            self.action_refresh()
        except PortainerAPIError as e:
            self.notify(str(e), severity="error")
