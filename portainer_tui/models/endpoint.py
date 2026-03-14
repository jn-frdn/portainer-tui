"""Portainer Endpoint (environment) model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class EndpointType(IntEnum):
    DOCKER = 1
    AGENT = 2
    AZURE = 3
    EDGE_AGENT = 4
    LOCAL = 5
    KUBERNETES = 6


@dataclass
class Endpoint:
    id: int
    name: str
    type: EndpointType
    url: str
    public_url: str = ""
    group_id: int = 1
    status: int = 1  # 1=up, 2=down
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> Endpoint:
        return cls(
            id=data["Id"],
            name=data["Name"],
            type=EndpointType(data.get("Type", 1)),
            url=data.get("URL", ""),
            public_url=data.get("PublicURL", ""),
            group_id=data.get("GroupId", 1),
            status=data.get("Status", 1),
            tags=data.get("TagIds", []),
        )

    @property
    def status_label(self) -> str:
        return "up" if self.status == 1 else "down"

    @property
    def type_label(self) -> str:
        labels = {
            EndpointType.DOCKER: "Docker",
            EndpointType.AGENT: "Agent",
            EndpointType.AZURE: "Azure ACI",
            EndpointType.EDGE_AGENT: "Edge Agent",
            EndpointType.LOCAL: "Local",
            EndpointType.KUBERNETES: "Kubernetes",
        }
        return labels.get(self.type, str(self.type))
