"""Container editor screen.

Allows editing ports, environment variables, network connections, and
restart policy of an existing container.

Because Docker has no "update container" API for most settings, changes
are applied via a stop → remove → recreate cycle using the original
inspect payload as a base.  The user is warned before this happens.
"""

from __future__ import annotations

import json
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from portainer_tui.api.client import PortainerAPIError, PortainerClient
from portainer_tui.models.container import Container
from portainer_tui.ui.widgets.confirm import ConfirmDialog


_RESTART_POLICIES = [
    ("no", "no — never restart"),
    ("always", "always — restart on any exit"),
    ("on-failure", "on-failure — restart only on non-zero exit"),
    ("unless-stopped", "unless-stopped — restart unless manually stopped"),
]


class ContainerEditorScreen(Screen[bool]):
    """Edit container ports, env vars, networks and restart policy.

    Dismisses with ``True`` if the container was recreated successfully.
    """

    DEFAULT_CSS = """
    ContainerEditorScreen { layout: vertical; }

    #editor-tabs { height: 1fr; }

    /* ── section headers ── */
    .section-title {
        background: $panel;
        color: $accent;
        text-style: bold;
        padding: 0 1;
        height: 1;
        margin-bottom: 1;
    }

    /* ── row forms (key / value pairs) ── */
    .row-form { height: auto; margin-bottom: 1; }
    .row-input { width: 1fr; margin-right: 1; }
    .row-del { width: 6; min-width: 6; }

    /* ── add-row bar ── */
    .add-bar { height: auto; margin-top: 1; }
    .add-input { width: 1fr; margin-right: 1; }
    .add-btn { width: 10; min-width: 10; }

    /* ── scrollable pane ── */
    .tab-scroll { height: 1fr; padding: 1 2; }

    /* ── restart policy tab ── */
    #restart-select { width: 1fr; margin-top: 1; }
    .policy-desc { color: $text-muted; margin-top: 1; padding: 0 1; }

    /* ── apply bar ── */
    #apply-bar {
        height: 3;
        background: $panel;
        layout: horizontal;
        align: right middle;
        padding: 0 2;
        dock: bottom;
    }
    #btn-apply { margin-left: 1; }
    #btn-cancel { }
    """

    BINDINGS = [
        Binding("ctrl+s", "apply", "Apply (recreate)", show=True),
        Binding("escape", "close", "Close", show=True),
    ]

    def __init__(
        self,
        client: PortainerClient,
        container: Container,
        endpoint_id: int,
        inspect_data: dict,
    ) -> None:
        super().__init__()
        self._client = client
        self._container = container
        self._endpoint_id = endpoint_id
        self._inspect = inspect_data

        # Parse current config into editable state
        cfg = inspect_data.get("Config", {})
        host_cfg = inspect_data.get("HostConfig", {})

        self._env: list[str] = list(cfg.get("Env") or [])
        self._ports: list[str] = self._parse_ports(host_cfg)
        self._restart_policy: str = host_cfg.get("RestartPolicy", {}).get("Name", "no")
        self._networks: list[str] = list(
            (inspect_data.get("NetworkSettings", {}).get("Networks") or {}).keys()
        )

    # ------------------------------------------------------------------
    # Parse helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_ports(host_cfg: dict) -> list[str]:
        """Convert PortBindings dict → list of 'host_port:container_port/proto' strings."""
        bindings = host_cfg.get("PortBindings") or {}
        result = []
        for container_port, host_list in bindings.items():
            if host_list:
                for h in host_list:
                    host_ip = h.get("HostIp", "")
                    host_port = h.get("HostPort", "")
                    prefix = f"{host_ip}:" if host_ip else ""
                    result.append(f"{prefix}{host_port}:{container_port}")
            else:
                result.append(f":{container_port}")
        return result

    @staticmethod
    def _ports_to_bindings(ports: list[str]) -> tuple[dict, dict]:
        """Convert port strings back to Docker ExposedPorts + PortBindings dicts."""
        exposed: dict[str, dict] = {}
        bindings: dict[str, list[dict]] = {}
        for entry in ports:
            entry = entry.strip()
            if not entry:
                continue
            # formats: host_port:container_port[/proto]
            #          ip:host_port:container_port[/proto]
            parts = entry.split(":")
            if len(parts) == 2:
                host_port, container_port = parts
                host_ip = ""
            elif len(parts) == 3:
                host_ip, host_port, container_port = parts
            else:
                continue
            if "/" not in container_port:
                container_port += "/tcp"
            exposed[container_port] = {}
            bindings.setdefault(container_port, []).append(
                {"HostIp": host_ip, "HostPort": host_port}
            )
        return exposed, bindings

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with TabbedContent(id="editor-tabs"):
            with TabPane("Ports", id="tab-ports"):
                with ScrollableContainer(classes="tab-scroll"):
                    yield Label("Port Bindings", classes="section-title")
                    yield Static(
                        "[dim]Format:  host_port:container_port/proto  "
                        "or  ip:host_port:container_port/proto[/]",
                        markup=True,
                    )
                    yield Vertical(id="ports-list")
                    with Horizontal(classes="add-bar"):
                        yield Input(
                            placeholder="e.g. 8080:80/tcp",
                            id="port-add-input",
                            classes="add-input",
                        )
                        yield Button("+ Add", id="port-add-btn", classes="add-btn")

            with TabPane("Environment", id="tab-env"):
                with ScrollableContainer(classes="tab-scroll"):
                    yield Label("Environment Variables", classes="section-title")
                    yield Static(
                        "[dim]Format:  KEY=value[/]", markup=True
                    )
                    yield Vertical(id="env-list")
                    with Horizontal(classes="add-bar"):
                        yield Input(
                            placeholder="e.g. MY_VAR=hello",
                            id="env-add-input",
                            classes="add-input",
                        )
                        yield Button("+ Add", id="env-add-btn", classes="add-btn")

            with TabPane("Networks", id="tab-networks"):
                with ScrollableContainer(classes="tab-scroll"):
                    yield Label("Connected Networks", classes="section-title")
                    yield Vertical(id="networks-list")
                    with Horizontal(classes="add-bar"):
                        yield Input(
                            placeholder="network name or ID",
                            id="net-add-input",
                            classes="add-input",
                        )
                        yield Button("+ Add", id="net-add-btn", classes="add-btn")

            with TabPane("Restart Policy", id="tab-restart"):
                with ScrollableContainer(classes="tab-scroll"):
                    yield Label("Restart Policy", classes="section-title")
                    yield Select(
                        options=[(label, val) for val, label in _RESTART_POLICIES],
                        value=self._restart_policy,
                        id="restart-select",
                    )

        with Horizontal(id="apply-bar"):
            yield Button("Cancel", id="btn-cancel", variant="default")
            yield Button("Apply (recreate container)", id="btn-apply", variant="warning")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Edit container — {self._container.name}"
        self._render_ports()
        self._render_env()
        self._render_networks()

    # ------------------------------------------------------------------
    # Render list rows
    # ------------------------------------------------------------------

    def _render_ports(self) -> None:
        container = self.query_one("#ports-list", Vertical)
        container.remove_children()
        for i, port in enumerate(self._ports):
            container.mount(self._make_row("port", i, port))

    def _render_env(self) -> None:
        container = self.query_one("#env-list", Vertical)
        container.remove_children()
        for i, var in enumerate(self._env):
            container.mount(self._make_row("env", i, var))

    def _render_networks(self) -> None:
        container = self.query_one("#networks-list", Vertical)
        container.remove_children()
        for i, net in enumerate(self._networks):
            container.mount(self._make_row("net", i, net))

    def _make_row(self, kind: str, idx: int, value: str) -> Horizontal:
        row = Horizontal(classes="row-form", id=f"row-{kind}-{idx}")
        inp = Input(value=value, classes="row-input", id=f"inp-{kind}-{idx}")
        btn = Button("✕", classes="row-del", id=f"del-{kind}-{idx}", variant="error")
        row.compose_add_child(inp)
        row.compose_add_child(btn)
        return row

    # ------------------------------------------------------------------
    # Button events
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""

        if bid == "port-add-btn":
            val = self.query_one("#port-add-input", Input).value.strip()
            if val:
                self._ports.append(val)
                self.query_one("#port-add-input", Input).value = ""
                self._render_ports()

        elif bid == "env-add-btn":
            val = self.query_one("#env-add-input", Input).value.strip()
            if val:
                self._env.append(val)
                self.query_one("#env-add-input", Input).value = ""
                self._render_env()

        elif bid == "net-add-btn":
            val = self.query_one("#net-add-input", Input).value.strip()
            if val:
                self._networks.append(val)
                self.query_one("#net-add-input", Input).value = ""
                self._render_networks()

        elif bid.startswith("del-port-"):
            idx = int(bid.split("-")[-1])
            self._sync_ports_from_inputs()
            self._ports.pop(idx)
            self._render_ports()

        elif bid.startswith("del-env-"):
            idx = int(bid.split("-")[-1])
            self._sync_env_from_inputs()
            self._env.pop(idx)
            self._render_env()

        elif bid.startswith("del-net-"):
            idx = int(bid.split("-")[-1])
            self._sync_networks_from_inputs()
            self._networks.pop(idx)
            self._render_networks()

        elif bid == "btn-apply":
            self.action_apply()

        elif bid == "btn-cancel":
            self.action_close()

    # ------------------------------------------------------------------
    # Sync edited input values back into state before saving
    # ------------------------------------------------------------------

    def _sync_ports_from_inputs(self) -> None:
        for i in range(len(self._ports)):
            try:
                self._ports[i] = self.query_one(f"#inp-port-{i}", Input).value
            except Exception:
                pass

    def _sync_env_from_inputs(self) -> None:
        for i in range(len(self._env)):
            try:
                self._env[i] = self.query_one(f"#inp-env-{i}", Input).value
            except Exception:
                pass

    def _sync_networks_from_inputs(self) -> None:
        for i in range(len(self._networks)):
            try:
                self._networks[i] = self.query_one(f"#inp-net-{i}", Input).value
            except Exception:
                pass

    def _sync_all(self) -> None:
        self._sync_ports_from_inputs()
        self._sync_env_from_inputs()
        self._sync_networks_from_inputs()
        # Restart policy
        sel = self.query_one("#restart-select", Select)
        if sel.value and sel.value is not Select.BLANK:
            self._restart_policy = str(sel.value)

    # ------------------------------------------------------------------
    # Apply (recreate)
    # ------------------------------------------------------------------

    def action_apply(self) -> None:
        self._do_apply()

    async def action_close(self) -> None:
        self.dismiss(False)

    @work(exclusive=True)
    async def _do_apply(self) -> None:
        self._sync_all()

        # Warn: this stops and removes the container
        was_running = self._container.state.value == "running"
        msg = (
            f"Applying changes to [bold]{self._container.name}[/] requires "
            f"{'stopping and ' if was_running else ''}recreating the container.\n\n"
            "The container will be briefly unavailable. Proceed?"
        )
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(msg, title="Recreate Container")
        )
        if not confirmed:
            return

        try:
            await self._recreate()
            self.notify(
                f"Container '{self._container.name}' recreated successfully",
                timeout=4,
            )
            self.dismiss(True)
        except PortainerAPIError as e:
            self.notify(f"Failed: {e}", severity="error")

    async def _recreate(self) -> None:
        """Stop (if running) → remove → create with new config → start."""
        client = self._client
        eid = self._endpoint_id
        cid = self._container.id
        name = self._container.name

        # 1. Stop if running
        if self._container.state.value == "running":
            await client.stop_container(eid, cid)

        # 2. Remove old container
        await client.remove_container(eid, cid, force=True)

        # 3. Build new create config from inspect data
        new_config = self._build_create_config()

        # 4. Create new container (same name)
        new_id = await client.create_container(eid, name, new_config)

        # 5. Connect to networks (beyond the first/default)
        # The HostConfig.NetworkMode handles the primary network;
        # extra networks are connected post-create.
        net_mode = new_config.get("HostConfig", {}).get("NetworkMode", "bridge")
        for net in self._networks:
            if net and net != net_mode:
                try:
                    await client.connect_network(eid, net, new_id)
                except PortainerAPIError:
                    pass  # best-effort

        # 6. Start
        await client.start_container(eid, new_id)

    def _build_create_config(self) -> dict[str, Any]:
        """Merge edited values back into the original inspect payload."""
        orig_cfg = self._inspect.get("Config", {})
        orig_host = self._inspect.get("HostConfig", {})

        exposed, bindings = self._ports_to_bindings(
            [p for p in self._ports if p.strip()]
        )

        env = [e for e in self._env if e.strip()]

        host_config = dict(orig_host)
        host_config["PortBindings"] = bindings
        host_config["RestartPolicy"] = {"Name": self._restart_policy, "MaximumRetryCount": 0}

        # Primary network: use first listed, fall back to original
        primary_net = self._networks[0] if self._networks else orig_host.get("NetworkMode", "bridge")
        host_config["NetworkMode"] = primary_net

        config: dict[str, Any] = {
            "Image": orig_cfg.get("Image", self._container.image),
            "Cmd": orig_cfg.get("Cmd"),
            "Entrypoint": orig_cfg.get("Entrypoint"),
            "Env": env,
            "ExposedPorts": {**orig_cfg.get("ExposedPorts", {}), **exposed},
            "Labels": orig_cfg.get("Labels", {}),
            "WorkingDir": orig_cfg.get("WorkingDir", ""),
            "User": orig_cfg.get("User", ""),
            "Volumes": orig_cfg.get("Volumes"),
            "HostConfig": host_config,
            "NetworkingConfig": {
                "EndpointsConfig": {
                    primary_net: {}
                }
            },
        }
        # Strip None values — Docker API rejects them for some fields
        return {k: v for k, v in config.items() if v is not None}
