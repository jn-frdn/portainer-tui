# portainer-tui

A terminal user interface for managing [Portainer](https://www.portainer.io/) instances, built with Python and [Textual](https://textual.textualize.io/).

Manage Docker containers, stacks, volumes, networks, and images — entirely from your terminal, without opening a browser.

---

## Features

- **Containers** — list, start, stop, restart, remove, view logs, inspect JSON, edit config (ports, env, networks, restart policy), pull latest image & restart
- **Stacks** — list, edit compose files with YAML syntax highlighting, remove, pull latest images & redeploy
- **Volumes** — list, inspect, remove
- **Networks** — list, inspect, remove
- **Images** — list, inspect, remove
- **Endpoints** — switch between multiple Portainer environments at runtime
- **Multiple instances** — configure many Portainer servers in one config file
- **Token & password auth** — API token (recommended) or username/password

---

## Screenshot

```
┌─────────────────────────────────────────────────────────────┐
│ Portainer TUI          instance: prod  |  endpoint: local   │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│Containers│  Stacks  │ Volumes  │ Networks │     Images     │
├──┬───────────────┬──────────────┬─────────┬────────┬───────┤
│  │ Name          │ Image        │ State   │ Status │ Ports │
├──┼───────────────┼──────────────┼─────────┼────────┼───────┤
│● │ nginx         │ nginx:latest │ running │ Up 2d  │ 80→80 │
│● │ postgres      │ postgres:16  │ running │ Up 2d  │       │
│● │ redis         │ redis:7      │ exited  │ Exited │       │
└──┴───────────────┴──────────────┴─────────┴────────┴───────┘
 e Edit  s Start  S Stop  R Restart  l Logs  i Inspect  d Del
```

---

## Requirements

- Python 3.11+
- Portainer CE or BE (v2.x)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

---

## Installation

### From source (recommended while in development)

```bash
git clone https://github.com/jn-frdn/portainer-tui.git
cd portainer-tui
uv sync
```

### With pip

```bash
pip install git+https://github.com/jn-frdn/portainer-tui.git
```

---

## Quick Start

### 1. Get a Portainer API token

In Portainer: **Account menu → My account → Access tokens → Add access token**

### 2. Configure credentials

**Option A — `.env` file** (loaded automatically):

```bash
cp .env.example .env
# edit .env
```

```dotenv
PORTAINER_URL=https://portainer.example.com
PORTAINER_TOKEN=ptr_xxxxxxxxxxxxxxxxxxxx
```

**Option B — environment variables**:

```bash
export PORTAINER_URL=https://portainer.example.com
export PORTAINER_TOKEN=ptr_xxxxxxxxxxxxxxxxxxxx
```

**Option C — CLI flags**:

```bash
portainer-tui --url https://portainer.example.com --token ptr_xxx
```

### 3. Run

```bash
uv run portainer-tui
# or, after pip install:
portainer-tui
```

---

## Configuration

Configuration is resolved in priority order: **CLI flags → environment variables → config file**.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `PORTAINER_URL` | Portainer base URL (no trailing slash) | **required** |
| `PORTAINER_TOKEN` | API token — preferred auth method | — |
| `PORTAINER_USERNAME` | Username for password auth | `admin` |
| `PORTAINER_PASSWORD` | Password for password auth | — |
| `PORTAINER_TLS_SKIP_VERIFY` | Skip TLS certificate verification | `false` |

### Config File

For multiple instances, create `~/.config/portainer-tui/config.yaml`:

```yaml
instances:
  - name: production
    url: https://portainer.example.com
    token: ptr_xxxxxxxxxxxxxxxxxxxx

  - name: staging
    url: https://staging.portainer.internal
    username: admin
    password: changeme
    tls_skip_verify: true
```

Switch between instances at runtime with `e` (endpoint picker).

### CLI Reference

```
Usage: portainer-tui [OPTIONS]

  Portainer TUI — manage your Portainer instances from the terminal.

Options:
  --url TEXT          Portainer base URL
  --token TEXT        Portainer API token
  --username TEXT     Portainer username
  --password TEXT     Portainer password
  --tls-skip-verify   Skip TLS certificate verification
  --config PATH       Path to config YAML file
  --help              Show this message and exit.
```

---

## Key Bindings

### Global

| Key | Action |
|---|---|
| `1` – `5` | Switch to Containers / Stacks / Volumes / Networks / Images |
| `e` | Open endpoint picker |
| `?` | Toggle help overlay |
| `q` / `ctrl+c` | Quit |

### Containers

| Key | Action |
|---|---|
| `r` | Refresh list |
| `e` | **Edit** container (ports, env vars, networks, restart policy) |
| `p` | **Pull & Restart** — pull latest image, then recreate container |
| `s` | Start |
| `S` | Stop |
| `R` | Restart |
| `l` | View logs |
| `i` | Inspect (JSON detail) |
| `d` | Remove (with confirmation) |

### Stacks

| Key | Action |
|---|---|
| `r` | Refresh list |
| `e` | **Edit** stack compose file (YAML editor) |
| `p` | **Pull & Redeploy** — pull latest images, then redeploy stack |
| `i` | View stack file (read-only) |
| `d` | Remove (with confirmation) |

### Volumes / Networks / Images

| Key | Action |
|---|---|
| `r` | Refresh list |
| `i` | Inspect (JSON detail) |
| `d` | Remove (with confirmation) |

### Stack Editor

| Key | Action |
|---|---|
| `ctrl+s` | Save |
| `esc` | Close (prompts if unsaved changes) |

### Container Editor

| Key | Action |
|---|---|
| `ctrl+s` | Apply changes (recreates container) |
| `esc` | Close without applying |

### Log Viewer

| Key | Action |
|---|---|
| `end` | Scroll to bottom |
| `q` / `esc` | Close |

---

## Container Editor

Press `e` on any container to open the editor. Changes are applied by **stopping, removing, and recreating** the container with the updated configuration — you will be asked to confirm before this happens.

**Ports tab** — edit port bindings using Docker format:
```
8080:80/tcp          # host_port:container_port/proto
0.0.0.0:443:443/tcp  # ip:host_port:container_port/proto
```

**Environment tab** — edit environment variables:
```
MY_VAR=hello
DATABASE_URL=postgres://...
```

**Networks tab** — connect or disconnect networks by name.

**Restart Policy tab** — choose from `no`, `always`, `on-failure`, or `unless-stopped`.

---

## Stack Editor

Press `e` on any stack to open a full-screen YAML editor with syntax highlighting. The editor tracks unsaved changes and warns before closing without saving. Save with `ctrl+s` — Portainer re-deploys the stack automatically.

---

## Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/jn-frdn/portainer-tui.git
cd portainer-tui
uv sync --extra dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=portainer_tui --cov-report=term-missing

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy portainer_tui/

# Textual dev console (live CSS reload + log output)
uv run textual run --dev portainer_tui/__main__.py
```

### Project Structure

```
portainer_tui/
├── __main__.py          # CLI entry point (Click)
├── config.py            # Config loading: env vars, YAML, CLI flags
├── api/
│   └── client.py        # Async Portainer REST API client (httpx)
├── models/              # Dataclasses for API response types
│   ├── container.py
│   ├── endpoint.py
│   ├── image.py
│   ├── network.py
│   ├── stack.py
│   └── volume.py
└── ui/
    ├── app.py           # Root Textual App — tab routing, endpoint state
    ├── screens/         # One screen/view per resource type
    │   ├── containers.py
    │   ├── container_editor.py
    │   ├── stacks.py
    │   ├── stack_editor.py
    │   ├── volumes.py
    │   ├── networks.py
    │   ├── images.py
    │   ├── endpoints.py
    │   └── _help.py
    └── widgets/         # Reusable components
        ├── confirm.py
        ├── logs.py
        ├── detail.py
        └── statusbar.py
```

### Adding a New Resource View

1. Add API methods to `portainer_tui/api/client.py`
2. Add a model dataclass to `portainer_tui/models/`
3. Create `portainer_tui/ui/screens/myresource.py` with a `MyResourceView(Widget)` class
4. Register the tab in `portainer_tui/ui/app.py` (`_TABS` list + import + `_rebuild_views`)
5. Add number-key binding to `app.py` `BINDINGS`

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss the approach.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes with tests where applicable
4. Run `uv run ruff check . && uv run pytest`
5. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE).
