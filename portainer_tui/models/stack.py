"""Portainer Stack model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class StackType(IntEnum):
    SWARM = 1
    COMPOSE = 2
    KUBERNETES = 3


class StackStatus(IntEnum):
    ACTIVE = 1
    INACTIVE = 2


@dataclass
class Stack:
    id: int
    name: str
    type: StackType
    endpoint_id: int
    status: StackStatus
    creation_date: int = 0
    update_date: int = 0
    created_by: str = ""
    updated_by: str = ""

    @classmethod
    def from_api(cls, data: dict) -> Stack:
        return cls(
            id=data["Id"],
            name=data["Name"],
            type=StackType(data.get("Type", 2)),
            endpoint_id=data.get("EndpointId", 0),
            status=StackStatus(data.get("Status", 1)),
            creation_date=data.get("CreationDate", 0),
            update_date=data.get("UpdateDate", 0),
            created_by=data.get("CreatedBy", ""),
            updated_by=data.get("UpdatedBy", ""),
        )

    @property
    def type_label(self) -> str:
        return {
            StackType.SWARM: "Swarm",
            StackType.COMPOSE: "Compose",
            StackType.KUBERNETES: "Kubernetes",
        }.get(self.type, str(self.type))

    @property
    def status_label(self) -> str:
        return "active" if self.status == StackStatus.ACTIVE else "inactive"
