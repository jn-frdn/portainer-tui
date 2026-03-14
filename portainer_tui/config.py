"""Configuration loading for portainer-tui."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised when the configuration is invalid or incomplete."""


@dataclass
class InstanceConfig:
    """Configuration for a single Portainer instance."""

    name: str
    url: str
    token: str | None = None
    username: str = "admin"
    password: str | None = None
    tls_skip_verify: bool = False

    def __post_init__(self) -> None:
        self.url = self.url.rstrip("/")
        if not self.token and not self.password:
            raise ConfigError(
                f"Instance '{self.name}' needs either 'token' or 'password' for authentication."
            )


@dataclass
class Config:
    """Top-level application configuration."""

    instances: list[InstanceConfig] = field(default_factory=list)

    @classmethod
    def load(
        cls,
        url: str | None = None,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        tls_skip_verify: bool = False,
        config_file: str | None = None,
    ) -> Config:
        """Load config from CLI flags, env vars, and/or config file.

        Priority: CLI flags > env vars > config file.
        """
        instances: list[InstanceConfig] = []

        # Load from config file first (lowest priority)
        file_path = _resolve_config_file(config_file)
        if file_path and file_path.exists():
            instances.extend(_load_from_file(file_path))

        # CLI / env var instance overrides or creates a single instance
        env_url = url or os.environ.get("PORTAINER_URL")
        if env_url:
            env_token = token or os.environ.get("PORTAINER_TOKEN")
            env_username = username or os.environ.get("PORTAINER_USERNAME", "admin")
            env_password = password or os.environ.get("PORTAINER_PASSWORD")
            env_skip = tls_skip_verify or (
                os.environ.get("PORTAINER_TLS_SKIP_VERIFY", "false").lower() == "true"
            )

            # Replace or prepend the "default" instance
            instances = [
                i for i in instances if i.name != "default"
            ]
            instances.insert(
                0,
                InstanceConfig(
                    name="default",
                    url=env_url,
                    token=env_token,
                    username=env_username,
                    password=env_password,
                    tls_skip_verify=env_skip,
                ),
            )

        if not instances:
            raise ConfigError(
                "No Portainer instance configured. "
                "Set PORTAINER_URL (and PORTAINER_TOKEN or PORTAINER_PASSWORD), "
                "or create ~/.config/portainer-tui/config.yaml."
            )

        return cls(instances=instances)

    @property
    def default_instance(self) -> InstanceConfig:
        return self.instances[0]


def _resolve_config_file(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "portainer-tui" / "config.yaml"


def _load_from_file(path: Path) -> list[InstanceConfig]:
    with path.open() as fh:
        data = yaml.safe_load(fh) or {}

    raw_instances = data.get("instances", [])
    if not isinstance(raw_instances, list):
        raise ConfigError(f"'instances' in {path} must be a list.")

    result = []
    for entry in raw_instances:
        try:
            result.append(
                InstanceConfig(
                    name=entry.get("name", "unnamed"),
                    url=entry["url"],
                    token=entry.get("token"),
                    username=entry.get("username", "admin"),
                    password=entry.get("password"),
                    tls_skip_verify=entry.get("tls_skip_verify", False),
                )
            )
        except KeyError as e:
            raise ConfigError(f"Missing field {e} in config instance entry: {entry}") from e

    return result
