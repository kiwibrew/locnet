"""Disk-backed storage for generated GeoJSON responses."""

import json
import logging
import os
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping


GEOJSON_CACHE_MAX_AGE = timedelta(days=30)
GEOJSON_CACHE_MAX_SIZE_BYTES = 1_000_000_000


class GeoJSONCache:
    """Disk-backed GeoJSON cache with fixed expiry and LRU size eviction."""

    def __init__(
        self,
        directory: str | Path,
        *,
        max_age: timedelta = GEOJSON_CACHE_MAX_AGE,
        max_size_bytes: int = GEOJSON_CACHE_MAX_SIZE_BYTES,
    ):
        if max_age.total_seconds() <= 0:
            raise ValueError("GeoJSON cache maximum age must be positive")
        if max_size_bytes < 0:
            raise ValueError("GeoJSON cache maximum size cannot be negative")

        self.directory = Path(directory)
        self.max_age_nanoseconds = int(max_age.total_seconds() * 1_000_000_000)
        self.max_size_bytes = max_size_bytes

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        now = time.time_ns()
        try:
            stat = path.stat()
            if now - stat.st_mtime_ns >= self.max_age_nanoseconds:
                path.unlink(missing_ok=True)
                return None

            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("cached GeoJSON is not an object")
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            logging.warning("Discarding unreadable GeoJSON cache entry %s", path)
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

        try:
            os.utime(path, ns=(now, stat.st_mtime_ns))
        except OSError:
            logging.warning("Unable to update GeoJSON cache recency for %s", path)
        return value

    def set(self, key: str, value: Mapping[str, Any]) -> None:
        encoded = json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        path = self._path(key)
        temporary_path: Path | None = None

        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=self.directory,
                prefix=f".{key}.",
                suffix=".tmp",
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(encoded)
            os.replace(temporary_path, path)
            self.prune()
        except OSError:
            logging.warning("Unable to write GeoJSON cache entry %s", path)
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError:
            logging.warning("Unable to delete GeoJSON cache entry for %s", key)

    def prune(self) -> None:
        """Remove expired entries, then evict least-recently-used entries."""
        now = time.time_ns()
        entries: list[tuple[int, Path, int]] = []

        try:
            paths = list(self.directory.glob("*.geojson"))
        except OSError:
            logging.warning("Unable to inspect the GeoJSON cache at %s", self.directory)
            return

        for path in paths:
            try:
                stat = path.stat()
                if now - stat.st_mtime_ns >= self.max_age_nanoseconds:
                    path.unlink(missing_ok=True)
                    continue
                entries.append((stat.st_atime_ns, path, stat.st_size))
            except FileNotFoundError:
                continue
            except OSError:
                logging.warning("Unable to inspect GeoJSON cache entry %s", path)

        total_size = sum(size for _, _, size in entries)
        for _, path, size in sorted(entries):
            if total_size <= self.max_size_bytes:
                break
            try:
                path.unlink(missing_ok=True)
                total_size -= size
            except OSError:
                logging.warning("Unable to evict GeoJSON cache entry %s", path)

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.geojson"
