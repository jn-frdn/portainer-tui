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
    in_use: bool | None = None

    @classmethod
    def from_api(cls, data: dict) -> Volume:
        usage = data.get("UsageData") or {}
        ref_count = usage.get("RefCount")
        in_use = (ref_count > 0) if ref_count is not None else None
        return cls(
            name=data["Name"],
            driver=data.get("Driver", "local"),
            mountpoint=data.get("Mountpoint", ""),
            scope=data.get("Scope", "local"),
            labels=data.get("Labels") or {},
            options=data.get("Options") or {},
            created_at=data.get("CreatedAt", ""),
            in_use=in_use,
        )
