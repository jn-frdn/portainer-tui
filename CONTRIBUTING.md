# Contributing to portainer-tui

Thank you for your interest in contributing!

## Getting started

```bash
git clone https://github.com/jn-frdn/portainer-tui.git
cd portainer-tui
uv sync --extra dev
```

## Before submitting a PR

```bash
uv run ruff check .       # lint
uv run ruff format .      # format
uv run mypy portainer_tui/  # type check
uv run pytest             # tests
```

All four must pass with no errors.

## Guidelines

- **Open an issue first** for significant changes or new features — it's good to align before writing code.
- **Keep PRs focused** — one thing per PR.
- **Add tests** for new API client methods and model parsing logic.
- **Follow existing patterns** — views are `Widget` subclasses, editors are `Screen` subclasses, API calls live exclusively in `api/client.py`.
- **No inline styles** — put CSS in `portainer_tui.tcss` or `DEFAULT_CSS` on the widget class.

## Reporting bugs

Please include:
- Your Portainer version
- Python version (`python --version`)
- The full traceback from the Textual error panel
- Steps to reproduce
