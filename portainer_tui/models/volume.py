"""Docker Volume model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Volume:
    name: str
    driver: str
    mountpoint: str
    scope: str
    labels: dict[str, str] = field(default_factory=dict)
    options: dict[str, str] = field(default_factory=dict)
    created_at: str = ""

    @classmethod
    def from_api(cls, data: dict) -> Volume:
        return cls(
            name=data["Name"],
            driver=data.get("Driver", "local"),
            mountpoint=data.get("Mountpoint", ""),
            scope=data.get("Scope", "local"),
            labels=data.get("Labels") or {},
            options=data.get("Options") or {},
            created_at=data.get("CreatedAt", ""),
        )
