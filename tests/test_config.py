"""Tests for config loading."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from portainer_tui.config import Config, ConfigError, InstanceConfig


def test_instance_config_token_auth() -> None:
    ic = InstanceConfig(name="test", url="http://localhost:9000", token="ptr_abc")
    assert ic.url == "http://localhost:9000"
    assert ic.token == "ptr_abc"


def test_instance_config_trailing_slash_stripped() -> None:
    ic = InstanceConfig(name="test", url="http://localhost:9000/", token="ptr_abc")
    assert ic.url == "http://localhost:9000"


def test_instance_config_no_auth_raises() -> None:
    with pytest.raises(ConfigError, match="authentication"):
        InstanceConfig(name="test", url="http://localhost:9000")


def test_config_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORTAINER_URL", "http://portainer.local:9000")
    monkeypatch.setenv("PORTAINER_TOKEN", "ptr_xyz")
    config = Config.load()
    assert len(config.instances) == 1
    assert config.default_instance.url == "http://portainer.local:9000"
    assert config.default_instance.token == "ptr_xyz"


def test_config_load_no_config_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PORTAINER_URL", raising=False)
    monkeypatch.delenv("PORTAINER_TOKEN", raising=False)
    monkeypatch.delenv("PORTAINER_PASSWORD", raising=False)
    # Point config file to a nonexistent path
    config_file = str(tmp_path / "no-config.yaml")
    with pytest.raises(ConfigError):
        Config.load(config_file=config_file)


def test_config_load_from_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent("""
        instances:
          - name: prod
            url: https://portainer.example.com
            token: ptr_prod
          - name: staging
            url: https://staging.example.com
            username: admin
            password: secret
        """)
    )
    config = Config.load(config_file=str(config_file))
    assert len(config.instances) == 2
    assert config.instances[0].name == "prod"
    assert config.instances[1].name == "staging"
    assert config.instances[1].password == "secret"
