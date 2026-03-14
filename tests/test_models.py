"""Tests for data models."""

from __future__ import annotations

from portainer_tui.models.container import Container, ContainerState
from portainer_tui.models.endpoint import Endpoint, EndpointType
from portainer_tui.models.image import Image
from portainer_tui.models.network import Network
from portainer_tui.models.stack import Stack, StackStatus, StackType
from portainer_tui.models.volume import Volume


def test_container_from_api() -> None:
    data = {
        "Id": "abc123def456",
        "Names": ["/my-container"],
        "Image": "nginx:latest",
        "ImageID": "sha256:abc",
        "Command": "nginx -g daemon off;",
        "Created": 1700000000,
        "State": "running",
        "Status": "Up 2 hours",
        "Ports": [{"PublicPort": 80, "PrivatePort": 80, "Type": "tcp"}],
        "Labels": {"com.docker.compose.project": "myapp"},
    }
    c = Container.from_api(data)
    assert c.short_id == "abc123def456"
    assert c.name == "my-container"
    assert c.state == ContainerState.RUNNING
    assert c.stack_name == "myapp"
    assert "80->80/tcp" in c.port_summary


def test_container_unknown_state() -> None:
    data = {
        "Id": "xyz",
        "Names": [],
        "Image": "",
        "ImageID": "",
        "Command": "",
        "Created": 0,
        "State": "bogus",
        "Status": "",
    }
    c = Container.from_api(data)
    assert c.state == ContainerState.UNKNOWN


def test_endpoint_from_api() -> None:
    data = {
        "Id": 1,
        "Name": "local",
        "Type": 1,
        "URL": "unix:///var/run/docker.sock",
        "PublicURL": "",
        "GroupId": 1,
        "Status": 1,
    }
    ep = Endpoint.from_api(data)
    assert ep.type == EndpointType.DOCKER
    assert ep.status_label == "up"
    assert ep.type_label == "Docker"


def test_image_size_human() -> None:
    img = Image(
        id="sha256:abc",
        repo_tags=["nginx:latest"],
        repo_digests=[],
        size=150 * 1024 * 1024,
        created=0,
    )
    assert "MB" in img.size_human
    assert img.short_id == "abc"


def test_volume_from_api() -> None:
    data = {
        "Name": "my-vol",
        "Driver": "local",
        "Mountpoint": "/var/lib/docker/volumes/my-vol/_data",
        "Scope": "local",
    }
    v = Volume.from_api(data)
    assert v.name == "my-vol"


def test_network_subnets() -> None:
    data = {
        "Id": "abc123",
        "Name": "bridge",
        "Driver": "bridge",
        "Scope": "local",
        "IPAM": {"Driver": "default", "Config": [{"Subnet": "172.17.0.0/16"}]},
    }
    n = Network.from_api(data)
    assert "172.17.0.0/16" in n.subnets


def test_stack_from_api() -> None:
    data = {
        "Id": 5,
        "Name": "mystack",
        "Type": 2,
        "EndpointId": 1,
        "Status": 1,
        "CreatedBy": "admin",
    }
    s = Stack.from_api(data)
    assert s.type == StackType.COMPOSE
    assert s.status == StackStatus.ACTIVE
    assert s.type_label == "Compose"
    assert s.status_label == "active"
