"""Docker Image model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Image:
    id: str
    repo_tags: list[str]
    repo_digests: list[str]
    size: int
    created: int
    labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> Image:
        return cls(
            id=data["Id"],
            repo_tags=data.get("RepoTags") or [],
            repo_digests=data.get("RepoDigests") or [],
            size=data.get("Size", 0),
            created=data.get("Created", 0),
            labels=(data.get("Labels") or {}),
        )

    @property
    def short_id(self) -> str:
        # Strip "sha256:" prefix if present
        raw = self.id.replace("sha256:", "")
        return raw[:12]

    @property
    def tag(self) -> str:
        return self.repo_tags[0] if self.repo_tags else "<none>"

    @property
    def size_human(self) -> str:
        mb = self.size / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.1f} GB"
        return f"{mb:.1f} MB"
