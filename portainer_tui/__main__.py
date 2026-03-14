"""Entry point for `python -m portainer_tui` and the `portainer-tui` script."""

from __future__ import annotations

import sys

import click
from dotenv import load_dotenv

load_dotenv()

from portainer_tui.config import Config, ConfigError
from portainer_tui.ui.app import PortainerApp


@click.command()
@click.option("--url", envvar="PORTAINER_URL", default=None, help="Portainer base URL")
@click.option("--token", envvar="PORTAINER_TOKEN", default=None, help="Portainer API token")
@click.option(
    "--username", envvar="PORTAINER_USERNAME", default=None, help="Portainer username"
)
@click.option(
    "--password", envvar="PORTAINER_PASSWORD", default=None, help="Portainer password"
)
@click.option(
    "--tls-skip-verify",
    envvar="PORTAINER_TLS_SKIP_VERIFY",
    is_flag=True,
    default=False,
    help="Skip TLS certificate verification",
)
@click.option(
    "--config",
    "config_file",
    default=None,
    type=click.Path(exists=False),
    help="Path to config YAML file",
)
def main(
    url: str | None,
    token: str | None,
    username: str | None,
    password: str | None,
    tls_skip_verify: bool,
    config_file: str | None,
) -> None:
    """Portainer TUI — manage your Portainer instances from the terminal."""
    try:
        config = Config.load(
            url=url,
            token=token,
            username=username,
            password=password,
            tls_skip_verify=tls_skip_verify,
            config_file=config_file,
        )
    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    app = PortainerApp(config=config)
    app.run()


if __name__ == "__main__":
    main()
