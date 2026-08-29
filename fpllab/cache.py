"""Small disk cache so repeated runs don't hammer the public endpoints."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

DEFAULT_DIR = Path.home() / ".fpllab" / "cache"


class Cache:
    def __init__(self, directory: Optional[Path] = None, ttl_seconds: int = 6 * 3600):
        self.dir = Path(directory) if directory else DEFAULT_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds

    def _path(self, key: str) -> Path:
        return self.dir / f"{hashlib.sha256(key.encode()).hexdigest()[:24]}.json"

    def get(self, key: str) -> Any:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if self.ttl and (time.time() - payload.get("_ts", 0)) > self.ttl:
            return None
        return payload.get("data")

    def set(self, key: str, data: Any) -> None:
        tmp = {"_ts": time.time(), "_key": key, "data": data}
        self._path(key).write_text(json.dumps(tmp))

    def clear(self) -> int:
        count = 0
        for file in self.dir.glob("*.json"):
            file.unlink()
            count += 1
        return count
