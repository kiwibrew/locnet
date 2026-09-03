import json
import os
import time
import unittest
from datetime import timedelta
from tempfile import TemporaryDirectory

from app.services.geojson_cache import (
    GEOJSON_CACHE_MAX_AGE,
    GEOJSON_CACHE_MAX_SIZE_BYTES,
    GeoJSONCache,
)


def cached_geojson(marker: str) -> dict:
    return {
        "type": "Feature",
        "properties": {"marker": marker},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
    }


def encoded_size(value: dict) -> int:
    return len(
        json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


class GeoJSONCacheTests(unittest.TestCase):
    def test_default_retention_limits_match_the_cache_policy(self):
        self.assertEqual(GEOJSON_CACHE_MAX_AGE, timedelta(days=30))
        self.assertEqual(GEOJSON_CACHE_MAX_SIZE_BYTES, 1_000_000_000)

    def test_get_returns_stored_geojson_and_preserves_creation_time(self):
        with TemporaryDirectory() as directory:
            cache = GeoJSONCache(directory)
            value = cached_geojson("a")
            cache.set("first", value)
            path = next(cache.directory.glob("*.geojson"))
            creation_time = path.stat().st_mtime

            self.assertEqual(cache.get("first"), value)
            self.assertEqual(path.stat().st_mtime, creation_time)

    def test_entry_expires_after_thirty_days(self):
        with TemporaryDirectory() as directory:
            cache = GeoJSONCache(directory)
            cache.set("expired", cached_geojson("a"))
            path = next(cache.directory.glob("*.geojson"))
            expired_time = time.time() - timedelta(days=31).total_seconds()
            os.utime(path, (expired_time, expired_time))

            self.assertIsNone(cache.get("expired"))
            self.assertFalse(path.exists())

    def test_size_limit_evicts_least_recently_used_entry(self):
        first = cached_geojson("a")
        second = cached_geojson("b")
        third = cached_geojson("c")
        entry_size = encoded_size(first)

        with TemporaryDirectory() as directory:
            cache = GeoJSONCache(directory, max_size_bytes=entry_size * 2)
            cache.set("first", first)
            cache.set("second", second)

            now = time.time()
            first_path = cache._path("first")
            second_path = cache._path("second")
            os.utime(first_path, (now - 10, first_path.stat().st_mtime))
            os.utime(second_path, (now - 5, second_path.stat().st_mtime))
            self.assertEqual(cache.get("first"), first)

            cache.set("third", third)

            self.assertEqual(cache.get("first"), first)
            self.assertIsNone(cache.get("second"))
            self.assertEqual(cache.get("third"), third)
            self.assertEqual(len(list(cache.directory.glob("*.geojson"))), 2)

    def test_prune_removes_expired_entries_before_size_eviction(self):
        first = cached_geojson("a")
        second = cached_geojson("b")

        with TemporaryDirectory() as directory:
            cache = GeoJSONCache(
                directory,
                max_age=timedelta(days=30),
                max_size_bytes=encoded_size(first),
            )
            cache.set("expired", first)
            expired_path = cache._path("expired")
            expired_time = time.time() - timedelta(days=31).total_seconds()
            os.utime(expired_path, (expired_time, expired_time))

            cache.set("current", second)

            self.assertFalse(expired_path.exists())
            self.assertEqual(cache.get("current"), second)


if __name__ == "__main__":
    unittest.main()
