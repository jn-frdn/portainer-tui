"""Root Textual application."""

from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header, Label, TabbedContent, TabPane

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.config import Config, InstanceConfig
from portainer_tui.models.endpoint import Endpoint
from portainer_tui.ui.screens.containers import ContainersView
from portainer_tui.ui.screens.endpoints import EndpointsScreen
from portainer_tui.ui.screens.images import ImagesView
from portainer_tui.ui.screens.networks import NetworksView
from portainer_tui.ui.screens.stacks import StacksView
from portainer_tui.ui.screens.volumes import VolumesView
from portainer_tui.ui.widgets.sysmon import SystemMonitor


_TABS = [
    ("containers", "Containers"),
    ("stacks", "Stacks"),
    ("volumes", "Volumes"),
    ("networks", "Networks"),
    ("images", "Images"),
]


class PortainerApp(App):
    """The main Portainer TUI application."""

    TITLE = "Portainer TUI"
    CSS_PATH = "../../portainer_tui.tcss"

    BINDINGS = [
        Binding("1", "switch_tab('containers')", "Containers", show=False),
        Binding("2", "switch_tab('stacks')", "Stacks", show=False),
        Binding("3", "switch_tab('volumes')", "Volumes", show=False),
        Binding("4", "switch_tab('networks')", "Networks", show=False),
        Binding("5", "switch_tab('images')", "Images", show=False),
        Binding("e", "pick_endpoint", "Endpoints"),
        Binding("?", "toggle_help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    current_endpoint: reactive[Endpoint | None] = reactive(None)

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._instance: InstanceConfig = config.default_instance
        self._client = PortainerClient(self._instance)

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield SystemMonitor()
        with TabbedContent(id="tabs"):
            for tab_id, tab_label in _TABS:
                with TabPane(tab_label, id=tab_id):
                    yield Label("Loading…", id=f"{tab_id}-placeholder")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.sub_title = f"instance: {self._instance.name}"
        self._load_initial_endpoint()

    async def on_unmount(self) -> None:
        await self._client.aclose()

    @work(exclusive=True)
    async def _load_initial_endpoint(self) -> None:
        """Connect to Portainer and load the first available endpoint."""
        try:
            await self._client.connect()
            endpoints = await self._client.list_endpoints()
            if endpoints:
                self.current_endpoint = endpoints[0]
        except PortainerAPIError as e:
            self.notify(f"Failed to load endpoints: {e}", severity="error")

    # ------------------------------------------------------------------
    # Reactive watchers
    # ------------------------------------------------------------------

    def watch_current_endpoint(self, endpoint: Endpoint | None) -> None:
        if endpoint is None:
            return
        self.sub_title = f"instance: {self._instance.name}  |  endpoint: {endpoint.name}"
        self._rebuild_views(endpoint)

    def _rebuild_views(self, endpoint: Endpoint) -> None:
        """Replace placeholder labels with real view widgets for each tab."""
        eid = endpoint.id
        view_map = {
            "containers": ContainersView(self._client, eid),
            "stacks": StacksView(self._client, eid),
            "volumes": VolumesView(self._client, eid),
            "networks": NetworksView(self._client, eid),
            "images": ImagesView(self._client, eid),
        }

        for tab_id, view in view_map.items():
            pane = self.query_one(f"TabPane#{tab_id}", TabPane)
            # Remove all existing children (placeholder or previous view)
            for child in list(pane.children):
                child.remove()
            pane.mount(view)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#tabs", TabbedContent).active = tab_id

    async def action_pick_endpoint(self) -> None:
        ep = await self.push_screen_wait(EndpointsScreen(self._client))
        if ep is not None:
            self.current_endpoint = ep

    def action_toggle_help(self) -> None:
        from portainer_tui.ui.screens._help import HelpScreen
        self.push_screen(HelpScreen())
