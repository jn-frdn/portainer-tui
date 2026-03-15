"""Portainer/Docker Container model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ContainerState(str, Enum):
    RUNNING = "running"
    EXITED = "exited"
    PAUSED = "paused"
    RESTARTING = "restarting"
    DEAD = "dead"
    CREATED = "created"
    REMOVING = "removing"
    UNKNOWN = "unknown"


@dataclass
class Container:
    id: str
    names: list[str]
    image: str
    image_id: str
    command: str
    created: int
    state: ContainerState
    status: str
    ports: list[dict] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    stack_name: str = ""
    volume_mounts: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> Container:
        state_str = data.get("State", "unknown").lower()
        try:
            state = ContainerState(state_str)
        except ValueError:
            state = ContainerState.UNKNOWN

        labels = data.get("Labels") or {}
        return cls(
            id=data["Id"],
            names=[n.lstrip("/") for n in data.get("Names", [])],
            image=data.get("Image", ""),
            image_id=data.get("ImageID", ""),
            command=data.get("Command", ""),
            created=data.get("Created", 0),
            state=state,
            status=data.get("Status", ""),
            ports=data.get("Ports", []),
            labels=labels,
            stack_name=labels.get("com.docker.compose.project", ""),
            volume_mounts=[
                m["Name"]
                for m in (data.get("Mounts") or [])
                if m.get("Type") == "volume" and m.get("Name")
            ],
        )

    @property
    def short_id(self) -> str:
        return self.id[:12]

    @property
    def name(self) -> str:
        return self.names[0] if self.names else self.short_id

    @property
    def port_summary(self) -> str:
        parts = []
        for p in self.ports:
            ip = p.get("IP", "")
            pub = p.get("PublicPort", "")
            priv = p.get("PrivatePort", "")
            proto = p.get("Type", "tcp")
            if pub:
                prefix = f"{ip}:" if ip else ""
                parts.append(f"{prefix}{pub}->{priv}/{proto}")
            else:
                parts.append(f"{priv}/{proto}")
        return ", ".join(parts)
