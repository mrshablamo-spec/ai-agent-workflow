from __future__ import annotations

import hashlib
from pathlib import Path

from supply_chain_intel.config import settings


class FileCache:
    def __init__(self, namespace: str):
        self.root = settings.cache_dir / namespace
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str, suffix: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.{suffix}"

    def get_text(self, key: str, suffix: str = "txt") -> str | None:
        path = self.path_for(key, suffix)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def set_text(self, key: str, value: str, suffix: str = "txt") -> Path:
        path = self.path_for(key, suffix)
        path.write_text(value, encoding="utf-8")
        return path
