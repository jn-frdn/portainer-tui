"""Docker Network model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Network:
    id: str
    name: str
    driver: str
    scope: str
    internal: bool = False
    attachable: bool = False
    ipam_driver: str = "default"
    subnets: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> Network:
        ipam = data.get("IPAM") or {}
        ipam_config = ipam.get("Config") or []
        subnets = [c.get("Subnet", "") for c in ipam_config if c.get("Subnet")]
        return cls(
            id=data["Id"],
            name=data["Name"],
            driver=data.get("Driver", ""),
            scope=data.get("Scope", ""),
            internal=data.get("Internal", False),
            attachable=data.get("Attachable", False),
            ipam_driver=ipam.get("Driver", "default"),
            subnets=subnets,
            labels=data.get("Labels") or {},
        )

    @property
    def short_id(self) -> str:
        return self.id[:12]
