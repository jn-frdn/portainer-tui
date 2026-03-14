"""Images view widget."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import DataTable, Label, LoadingIndicator

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.image import Image
from portainer_tui.ui.widgets.confirm import ConfirmDialog


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

    def compose(self) -> ComposeResult:
        yield LoadingIndicator(id="loading")
        table = DataTable(id="images-table", cursor_type="row")
        table.add_columns("ID", "Tag", "Size")
        table.display = False
        yield table
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

    def _populate_table(self) -> None:
        table = self.query_one("#images-table", DataTable)
        empty = self.query_one("#empty-label", Label)
        table.clear()
        if not self._images:
            table.display = False
            empty.display = True
            return
        table.display = True
        empty.display = False
        for img in self._images:
            table.add_row(img.short_id, img.tag, img.size_human, key=img.id)

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = loading

    def _selected_image(self) -> Image | None:
        table = self.query_one("#images-table", DataTable)
        if table.cursor_row is None or not self._images:
            return None
        try:
            return self._images[table.cursor_row]
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
